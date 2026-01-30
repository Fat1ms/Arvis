"""
Generate icon files for Arvis Launcher and Client
Cyan-to-Purple gradient sphere design
Requires: Pillow (pip install pillow)
"""

from pathlib import Path
import math

def create_gradient_sphere_icon():
    """Create a cyan-to-purple gradient sphere icon"""
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        print("Installing Pillow...")
        import subprocess
        subprocess.run(["pip", "install", "pillow"])
        from PIL import Image, ImageDraw, ImageFilter
    
    # Create icons at multiple sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
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
                    
                    # Vertical gradient factor (0 at top, 1 at bottom)
                    t = (dy / radius + 1) / 2
                    
                    # Color gradient: Cyan (top) to Purple/Violet (bottom)
                    # Top: Bright cyan (0, 200, 255)
                    # Bottom: Purple/Violet (138, 43, 226) or (148, 0, 211)
                    
                    r1, g1, b1 = 0, 210, 255     # Cyan (top)
                    r2, g2, b2 = 138, 43, 226   # Blue-Violet (bottom)
                    
                    # Smooth gradient interpolation
                    r = int(r1 + (r2 - r1) * t)
                    g = int(g1 + (g2 - g1) * t)
                    b = int(b1 + (b2 - b1) * t)
                    
                    # Light position for 3D sphere effect (top-left)
                    light_x, light_y = -0.35, -0.35
                    light_dist = math.sqrt((dx/radius - light_x)**2 + (dy/radius - light_y)**2)
                    light_factor = max(0, 1 - light_dist * 0.6)
                    
                    # Add highlight (brighter near light source)
                    highlight = light_factor * 0.35
                    r = min(255, int(r + highlight * (255 - r)))
                    g = min(255, int(g + highlight * (255 - g)))
                    b = min(255, int(b + highlight * (255 - b)))
                    
                    # Edge darkening for sphere depth
                    edge_factor = 1 - (norm_dist ** 2.5) * 0.25
                    r = int(r * edge_factor)
                    g = int(g * edge_factor)
                    b = int(b * edge_factor)
                    
                    # Soft edge (anti-aliasing)
                    if dist > radius - 1.5:
                        alpha = int(255 * max(0, min(1, (radius - dist + 1.5) / 1.5)))
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
    import shutil
    
    base_dir = Path(__file__).parent
    resources_dir = base_dir / "resources"
    resources_dir.mkdir(exist_ok=True)
    
    # Client directories to update
    client_dirs = [
        base_dir.parent / "Arvis-Client",
        base_dir.parent / "Arvis-Client-master",
    ]
    
    print("Generating cyan-to-purple gradient sphere icons...")
    images = create_gradient_sphere_icon()
    
    # Save as ICO (Windows) - main icon
    ico_path = resources_dir / "arvis.ico"
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images[:6]],  # ICO supports up to 256
        append_images=images[1:6]
    )
    print(f"Created: {ico_path}")
    
    # Save largest as PNG
    png_path = resources_dir / "arvis.png"
    images[-1].save(png_path, format='PNG')
    print(f"Created: {png_path}")
    
    # Save PNG at 256px for launcher
    png_256_path = resources_dir / "arvis_launcher.png"
    images[-2].save(png_256_path, format='PNG')  # 256px
    print(f"Created: {png_256_path}")
    
    # Also save with specific names for compatibility
    for name in ["arvis_launcher.ico", "arvis_client.ico"]:
        path = resources_dir / name
        images[0].save(
            path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images[:6]],
            append_images=images[1:6]
        )
        print(f"Created: {path}")
    
    # Copy icon to client directories
    for client_dir in client_dirs:
        if client_dir.exists():
            dest = client_dir / "icon.ico"
            shutil.copy(ico_path, dest)
            print(f"Copied to: {dest}")
            
            # Also save PNG for client
            dest_png = client_dir / "icon.png"
            images[-2].save(dest_png, format='PNG')
            print(f"Created: {dest_png}")
    
    print("\n✅ Done! Icons updated in launcher and client.")


if __name__ == "__main__":
    main()
