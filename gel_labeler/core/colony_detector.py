import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional


class ColonyObject:
    """Represents an individual detected or manually added colony / seed."""
    def __init__(self, obj_id: int, x: float, y: float, radius: float = 8.0, 
                 area: float = 0.0, is_manual: bool = False, color: str = "#FF3366"):
        self.id = obj_id
        self.x = float(x)
        self.y = float(y)
        self.radius = max(2.0, float(radius))
        self.area = float(area) if area > 0 else np.pi * (self.radius ** 2)
        self.is_manual = is_manual
        self.color = color

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "radius": round(self.radius, 2),
            "area": round(self.area, 2),
            "is_manual": self.is_manual
        }


class ColonyDetector:
    """Computer vision engine for automated colony and seed counting."""

    @staticmethod
    def calculate_cfu(count: int, plated_volume_ml: float, dilution_factor: float) -> float:
        """Calculates Colony Forming Units per mL (CFU/mL).
        
        Formula: CFU/mL = (Count * Dilution Factor) / Plated Volume (mL)
        """
        if plated_volume_ml <= 0:
            return 0.0
        return float(count * dilution_factor / plated_volume_ml)

    @staticmethod
    def detect_petri_dish_circle(image: np.ndarray) -> Optional[Tuple[int, int, int]]:
        """Detects the circular rim of a petri dish to mask out edge noise.
        
        Returns: (center_x, center_y, radius) or None
        """
        if image is None or len(image.shape) < 2:
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape
        min_dim = min(h, w)
        
        blurred = cv2.medianBlur(gray, 7)
        circles = cv2.HoughCircles(
            blurred, 
            cv2.HOUGH_GRADIENT, 
            dp=1.2, 
            minDist=int(min_dim * 0.4),
            param1=100, 
            param2=30, 
            minRadius=int(min_dim * 0.3), 
            maxRadius=int(min_dim * 0.52)
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            best = circles[0][0]
            cx, cy, r = int(best[0]), int(best[1]), int(best[2])
            r = min(r, cx, cy, w - cx, h - cy)
            return (cx, cy, max(10, r))
            
        # Fallback to centered inscribed circle
        return (w // 2, h // 2, int(min_dim * 0.46))

    @staticmethod
    def detect_colonies(
        image: np.ndarray,
        min_radius: int = 4,
        max_radius: int = 50,
        sensitivity: int = 50,
        circularity_min: float = 0.3,
        invert_mode: bool = False,
        mask_petri_dish: bool = True,
        use_watershed: bool = True
    ) -> Tuple[List[ColonyObject], Optional[Tuple[int, int, int]]]:
        """Detects bacterial colonies or seeds in an image using adaptive segmentation and watershed.
        
        Args:
            image: Input RGB/BGR image as numpy array.
            min_radius: Minimum colony/seed radius in pixels.
            max_radius: Maximum colony/seed radius in pixels.
            sensitivity: Sensitivity slider (1 to 100). Higher = detects fainter/smaller colonies.
            circularity_min: Circularity threshold (0.0 to 1.0) to filter non-round debris.
            invert_mode: True if counting light colonies on dark background; False for dark on light.
            mask_petri_dish: Whether to auto-mask out the outer rim of the petri dish.
            use_watershed: Whether to apply distance-transform watershed for touching colonies.
            
        Returns:
            Tuple of (List of ColonyObjects, Petri dish circle (cx, cy, r))
        """
        if image is None:
            return [], None
            
        h, w = image.shape[:2]
        if h <= 10 or w <= 10:
            return [], None
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        
        # 1. Petri dish boundary masking
        dish_circle = None
        mask = np.ones((h, w), dtype=np.uint8) * 255
        if mask_petri_dish:
            dish_circle = ColonyDetector.detect_petri_dish_circle(image)
            if dish_circle:
                cx, cy, r = dish_circle
                dish_mask = np.zeros((h, w), dtype=np.uint8)
                # Inset circular mask slightly (94% radius) to completely avoid rim artifacts
                cv2.circle(dish_mask, (cx, cy), int(r * 0.94), 255, -1)
                mask = dish_mask
                
        # 2. Gaussian Denoising
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. Adaptive Thresholding
        sens = max(1, min(100, sensitivity))
        block_size = int(max(15, (w / 25)))
        if block_size % 2 == 0:
            block_size += 1
            
        # Map sensitivity 1..100 -> C offset (approx 15 to 2)
        c_offset = max(1, int((105 - sens) * 0.16))
        
        thresh_type = cv2.THRESH_BINARY if invert_mode else cv2.THRESH_BINARY_INV
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresh_type, block_size, c_offset
        )
        
        # Apply petri dish mask
        binary = cv2.bitwise_and(binary, binary, mask=mask)
        
        # Morphological opening to remove salt noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        
        colonies: List[ColonyObject] = []
        next_id = 1
        
        if use_watershed:
            # 4. Distance Transform & Peak Watershed
            dist_transform = cv2.distanceTransform(opened, cv2.DIST_L2, 5)
            max_d = dist_transform.max()
            
            if max_d > 0:
                dist_thresh = max(0.08, min(0.60, 0.28 - (sens - 50) * 0.003))
                ret, sure_fg = cv2.threshold(dist_transform, dist_thresh * max_d, 255, cv2.THRESH_BINARY)
                sure_fg = np.uint8(sure_fg)
                
                # Markers for connected components
                ret, markers = cv2.connectedComponents(sure_fg)
                markers = markers + 1
                sure_bg = cv2.dilate(opened, kernel, iterations=2)
                unknown = cv2.subtract(sure_bg, sure_fg)
                markers[unknown == 255] = 0
                
                color_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                markers = cv2.watershed(color_img, markers.astype(np.int32))
                
                unique_markers = np.unique(markers)
                for m_id in unique_markers:
                    if m_id <= 1:
                        continue
                    colony_mask = np.uint8(markers == m_id)
                    contours, _ = cv2.findContours(colony_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if not contours:
                        continue
                    cnt = contours[0]
                    area = cv2.contourArea(cnt)
                    min_area = np.pi * (min_radius ** 2) * 0.5
                    max_area = np.pi * (max_radius ** 2) * 1.8
                    
                    if area < min_area or area > max_area:
                        continue
                        
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        circ = 4 * np.pi * (area / (perimeter * perimeter))
                        if circ < circularity_min:
                            continue
                            
                    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                    radius = max(float(min_radius), min(float(max_radius), float(radius)))
                    
                    colonies.append(ColonyObject(
                        obj_id=next_id,
                        x=float(cx),
                        y=float(cy),
                        radius=float(radius),
                        area=float(area),
                        is_manual=False
                    ))
                    next_id += 1
                    
        # Fallback to direct contour detection if watershed produced 0 results
        if len(colonies) == 0:
            contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                min_area = np.pi * (min_radius ** 2) * 0.5
                max_area = np.pi * (max_radius ** 2) * 1.8
                
                if area < min_area or area > max_area:
                    continue
                    
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circ = 4 * np.pi * (area / (perimeter * perimeter))
                    if circ < circularity_min:
                        continue
                        
                (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                radius = max(float(min_radius), min(float(max_radius), float(radius)))
                
                colonies.append(ColonyObject(
                    obj_id=next_id,
                    x=float(cx),
                    y=float(cy),
                    radius=float(radius),
                    area=float(area),
                    is_manual=False
                ))
                next_id += 1
                
        return colonies, dish_circle
