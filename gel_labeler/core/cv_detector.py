import cv2
import numpy as np
from typing import Tuple, List

def detect_lane_positions(image_path: str, y_start: int, expected_lanes: int = 30, 
                           scan_height: int = 150) -> List[float]:
    """Analyzes a horizontal slice of the gel image to find exact lane centers.
    
    Computes a smoothed vertical profile, identifies local peaks, interpolates 
    missing lanes (due to negative controls/blank samples) using median spacing,
    and returns the exact X coordinates for every lane.
    
    Returns:
        List[float] - Coordinates of detected well/lane centers.
    """
    if expected_lanes <= 0:
        return []
        
    # Load image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"CV Error: Could not read image path {image_path}")
        # Return evenly spaced coordinates as fallback
        return list(np.linspace(20, 1004, expected_lanes))
        
    img_h, img_w = img.shape
    y_end = min(img_h, y_start + scan_height)
    y_start = max(0, y_start)
    
    if y_start >= y_end:
        return list(np.linspace(20, img_w - 20, expected_lanes))
        
    # Crop to the region where DNA bands migrate for this tier
    roi = img[y_start:y_end, :]
    
    # Compute vertical projection profile (column-wise average intensity)
    profile = np.mean(roi, axis=0)
    
    # Smooth with Gaussian filter to reduce image noise and grain
    kernel_size = int(img_w / (expected_lanes * 5))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel_size = max(3, kernel_size)
    smoothed = cv2.GaussianBlur(profile, (kernel_size, 1), 0).flatten()
    
    # Extract local maxima (peaks)
    peaks = []
    # Minimum spacing constraint to prevent double-detecting broad bands
    min_dist = int(img_w / (expected_lanes * 1.6))
    
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1]:
            peaks.append((smoothed[i], i))
            
    # Sort peaks by intensity (descending)
    peaks.sort(key=lambda x: x[0], reverse=True)
    
    # Apply distance constraint filtering
    detected = []
    for val, idx in peaks:
        if all(abs(idx - p) > min_dist for p in detected):
            detected.append(idx)
            
    # Sort indices left-to-right
    detected.sort()
    
    # --- Resolve Count Discrepancies ---
    
    if len(detected) == expected_lanes:
        return [float(p) for p in detected]
        
    elif len(detected) > expected_lanes:
        # Too many peaks: keep the ones with the highest profile intensity
        val_peaks = [(smoothed[p], p) for p in detected]
        val_peaks.sort(key=lambda x: x[0], reverse=True)
        top_peaks = [p for val, p in val_peaks[:expected_lanes]]
        top_peaks.sort()
        return [float(p) for p in top_peaks]
        
    else:
        # Too few peaks: interpolate missing lanes and pad boundaries
        if len(detected) >= 2:
            spacings = [detected[i+1] - detected[i] for i in range(len(detected)-1)]
            dx = np.median(spacings)
        else:
            dx = img_w / expected_lanes
            
        filled = []
        if len(detected) > 0:
            filled.append(detected[0])
            for i in range(len(detected)-1):
                p1 = detected[i]
                p2 = detected[i+1]
                gap = p2 - p1
                # If gap is double the median spacing, insert virtual lane centers
                if gap > 1.6 * dx:
                    num_inserts = int(round(gap / dx)) - 1
                    insert_dx = gap / (num_inserts + 1)
                    for j in range(1, num_inserts + 1):
                        filled.append(p1 + j * insert_dx)
                filled.append(p2)
        else:
            # Fallback to even spacing if zero peaks detected
            return [float(20 + i * dx) for i in range(expected_lanes)]
            
        # Pad boundaries if we still have fewer than expected_lanes
        while len(filled) < expected_lanes:
            right_space = img_w - filled[-1]
            left_space = filled[0]
            if right_space >= left_space:
                filled.append(filled[-1] + dx)
            else:
                filled.insert(0, max(0.0, filled[0] - dx))
                
        # Trim if rounding caused an overflow
        if len(filled) > expected_lanes:
            filled = filled[:expected_lanes]
            
        return [float(p) for p in filled]

def detect_lane_grid_params(image_path: str, y_start: int, expected_lanes: int = 30, 
                            scan_height: int = 150) -> Tuple[float, float]:
    """Calculates fitted average X Start and Pitch for UI input displays."""
    xs = detect_lane_positions(image_path, y_start, expected_lanes, scan_height)
    n = len(xs)
    if n >= 2:
        x_indices = np.arange(n)
        y_coords = np.array(xs)
        # Linear regression: fit a straight line
        pitch, x_start = np.polyfit(x_indices, y_coords, 1)
        if pitch <= 1.0 or x_start < 0:
            return 20.0, 26.5
        return float(x_start), float(pitch)
    return 20.0, 26.5
