"""
Generate icon files for Arvis Launcher and Client
Based on the cyan/turquoise gradient sphere design
Requires: Pillow (pip install pillow)
"""

from pathlib import Path
import math

def create_gradient_sphere_icon():
    """Create a cyan/turquoise gradient sphere icon"""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        print("Installing Pillow...")
        import subprocess
        subprocess.run(["pip", "install", "pillow"])
        from PIL import Image, ImageDraw, ImageFilter
    
    # Create icons at multiple sizes
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # Create gradient sphere
        center_x, center_y = size // 2, size // 2
        radius = size // 2 - max(1, size // 32)
        
        # Draw pixel by pixel for smooth gradient
        for y in range(size):
            for x in range(size):
                dx = x - center_x
                dy = y - center_y
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist <= radius:
                    # Calculate normalized distance from center
                    norm_dist = dist / radius
                    
                    # Calculate angle for gradient direction (top-left to bottom-right feel)
                    angle = math.atan2(dy, dx)
                    angle_factor = (math.sin(angle - math.pi/4) + 1) / 2
                    
                    # Sphere shading: lighter at top-left, darker at edges
                    # Light position simulation
                    light_x, light_y = -0.4, -0.4
                    light_dist = math.sqrt((dx/radius - light_x)**2 + (dy/radius - light_y)**2)
                    light_factor = max(0, 1 - light_dist * 0.7)
                    
                    # Base colors: cyan to turquoise gradient
                    # Top: lighter cyan (140, 220, 255)
                    # Bottom: deeper turquoise (0, 200, 220)
                    
                    # Vertical gradient
                    t = (dy / radius + 1) / 2  # 0 at top, 1 at bottom
                    
                    # Color mixing
                    r1, g1, b1 = 140, 230, 255  # Light cyan (top)
                    r2, g2, b2 = 0, 200, 220    # Turquoise (bottom)
                    
                    r = int(r1 + (r2 - r1) * t)
                    g = int(g1 + (g2 - g1) * t)
                    b = int(b1 + (b2 - b1) * t)
                    
                    # Add highlight
                    highlight = light_factor * 0.4
                    r = min(255, int(r + highlight * (255 - r)))
                    g = min(255, int(g + highlight * (255 - g)))
                    b = min(255, int(b + highlight * (255 - b)))
                    
                    # Edge darkening for sphere effect
                    edge_factor = 1 - (norm_dist ** 2) * 0.3
                    r = int(r * edge_factor)
                    g = int(g * edge_factor)
                    b = int(b * edge_factor)
                    
                    # Soft edge (anti-aliasing)
                    if dist > radius - 1:
                        alpha = int(255 * (radius - dist + 1))
                    else:
                        alpha = 255
                    
                    img.putpixel((x, y), (r, g, b, alpha))
        
        # Apply slight blur for smoothness on larger sizes
        if size >= 64:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        images.append(img)
    
    return images


def main():
    """Generate icon files"""
    resources_dir = Path(__file__).parent / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    print("Generating cyan gradient sphere icons...")
    images = create_gradient_sphere_icon()
    
    # Save as ICO (Windows) - single icon for both launcher and client
    ico_path = resources_dir / "arvis.ico"
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    print(f"Created: {ico_path}")
    
    # Save largest as PNG
    png_path = resources_dir / "arvis.png"
    images[-1].save(png_path, format='PNG')
    print(f"Created: {png_path}")
    
    # Also save with specific names for compatibility
    for name in ["arvis_launcher.ico", "arvis_client.ico"]:
        path = resources_dir / name
        images[0].save(
            path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        print(f"Created: {path}")
    
    print("Done!")


if __name__ == "__main__":
    main()
