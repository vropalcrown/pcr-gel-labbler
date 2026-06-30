import os
from PIL import Image, ImageDraw, ImageFilter

def create_mock_gel(output_path="mock_gel.png"):
    # Create dark agarose gel background
    width, height = 800, 600
    # Create dark purple-black gradient/base to mimic ethidium bromide UV background
    image = Image.new("RGB", (width, height), color=(15, 10, 20))
    draw = ImageDraw.Draw(image)
    
    # Draw horizontal divider for buffer line/well line
    draw.rectangle([0, 0, width, height], fill=(12, 10, 18))
    
    # Draw 8 sample wells at the top
    well_y = 60
    well_width = 40
    well_height = 12
    well_spacing = 50
    start_x = 75
    
    wells = []
    for i in range(8):
        x1 = start_x + i * (well_width + well_spacing)
        y1 = well_y
        x2 = x1 + well_width
        y2 = y1 + well_height
        wells.append((x1, y1, x2, y2))
        # Well box (light gray border, dark interior)
        draw.rectangle([x1, y1, x2, y2], fill=(5, 4, 8), outline=(60, 60, 70), width=1)
        
    # Draw a DNA ladder in Lane 1
    # Ladder bands at regular intervals, descending in molecular weight (larger at top)
    ladder_x1, _, ladder_x2, _ = wells[0]
    ladder_bands_y = [120, 160, 210, 270, 340, 420, 510]
    for y in ladder_bands_y:
        # Draw glowing band
        # Outer glow
        draw.rectangle([ladder_x1 + 2, y - 4, ladder_x2 - 2, y + 4], fill=(120, 100, 255, 50))
        # Core band (bright fluorescent cyan-blue)
        draw.rectangle([ladder_x1 + 4, y - 2, ladder_x2 - 4, y + 2], fill=(160, 220, 255))

    # Draw PCR bands for other lanes (Lanes 2 to 8)
    # Different lanes will show varying products: some positive, some negative controls, some doublets
    lane_products = {
        1: [210],         # PCR product 1
        2: [210],         # PCR product 2
        3: [],            # Negative Control (No bands)
        4: [210, 340],    # Multiplex PCR (2 bands)
        5: [210],         # PCR product 3
        6: [340],         # PCR product 4 (larger amplicon)
        7: [210]          # Positive Control
    }
    
    for lane_idx, bands in lane_products.items():
        x1, _, x2, _ = wells[lane_idx]
        for y in bands:
            # Fluorescent Green/Yellow dye for PCR products
            # Outer glow
            draw.rectangle([x1 + 2, y - 5, x2 - 2, y + 5], fill=(30, 200, 30, 60))
            # Core band (bright fluorescent green)
            draw.rectangle([x1 + 4, y - 2, x2 - 4, y + 2], fill=(150, 255, 150))
            
    # Apply a slight Gaussian blur to make the DNA bands look organic and diffuse
    blurred_image = image.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Re-draw the wells crisp on top of the blurred bands
    draw_blurred = ImageDraw.Draw(blurred_image)
    for x1, y1, x2, y2 in wells:
        draw_blurred.rectangle([x1, y1, x2, y2], fill=(8, 5, 12), outline=(80, 80, 100), width=1)
        
    # Add a slight noise overlay to simulate digital CCD camera sensor noise
    # (very subtle, makes it look premium and real)
    import random
    pixels = blurred_image.load()
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            noise = random.randint(-4, 4)
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise))
            )
            
    blurred_image.save(output_path)
    print(f"Mock gel image saved to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    create_mock_gel()
