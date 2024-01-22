import os
import subprocess
from abc import ABC, abstractmethod
import shutil
import requests
from pathlib import Path
import typer
import platform
import bpy
import tempfile
import markdown
from .utils.dmgextractor import DMGExtractor
import fitz  # PyMuPDF
import commonmark
from pygments.formatters import HtmlFormatter
from markdown.extensions.codehilite import CodeHiliteExtension
from bpy.types import Sequence, Area
import math
from mathutils import Euler, Vector
from urllib.parse import urlparse
from PIL import Image
import io
import bmesh


class InkscapeInstallerFactory:
    @staticmethod
    def get_installer():
        if platform.system() == 'Windows':
            return WindowsInkscapeInstaller()
        elif platform.system() == 'Darwin':  # macOS
            return MacOSInkscapeInstaller()
        elif platform.system() == 'Linux':
            return LinuxInkscapeInstaller()
        else:
            raise NotImplementedError("Unsupported operating system")


class InkscapeInstaller(ABC):
    def __init__(self):
        self.install_path = Path.home() / ".md3d/inkscape"
        self.binary = None

    def is_installed(self):
        """Check if Inkscape is already installed."""
        return self.install_path.exists()

    @abstractmethod
    def install(self):
        """Install Inkscape."""
        pass

class WindowsInkscapeInstaller(InkscapeInstaller):
    def install(self):
        # Implementing Windows-specific installation logic
        inkscape_url = "https://inkscape.org/gallery/item/44622/inkscape-1.3.2_2023-11-25_091e20e-x64.7z"
        inkscape_path = self.install_path

        # Download Inkscape
        print("Downloading Inkscape for Windows...")
        response = requests.get(inkscape_url, stream=True)
        if response.status_code == 200:
            with open(inkscape_path / "inkscape.7z", 'wb') as f:
                f.write(response.content)
            print("Download completed.")

            # Extracting Inkscape
            print("Extracting Inkscape...")
            # Note: Use appropriate tool or library to extract .7z files
            # Example: using subprocess to call a tool like 7zip
            subprocess.run(["7z", "x", str(inkscape_path / "inkscape.7z"), "-o" + str(inkscape_path)], check=True)
            print("Inkscape installed successfully.")
        else:
            print("Failed to download Inkscape.")

class MacOSInkscapeInstaller(InkscapeInstaller):
    def __init__(self):
        super().__init__()
        self.binary = self.install_path / "Inkscape.app/Contents/MacOS/inkscape"
        
    def install(self):
        # Implementing MacOS-specific installation logic
        inkscape_url = "https://inkscape.org/gallery/item/44624/Inkscape-1.3.2_arm64.dmg"
        self.install_path.mkdir(parents=True, exist_ok=True)
        download_path = Path.home() / ".md3d"

        # Download Inkscape
        print("Downloading Inkscape for MacOS...")
        response = requests.get(inkscape_url, stream=True)
        if response.status_code == 200:
            dmg_path = download_path / "Inkscape.dmg"
            with open(dmg_path, 'wb') as f:
                f.write(response.content)
            print("Download completed.")

            # Mounting and installing Inkscape
            print("Installing Inkscape...")
            with DMGExtractor(dmg_path) as extractor:
                extractor.extractall(self.install_path)

        else:
            print("Failed to download Inkscape.")

class LinuxInkscapeInstaller(InkscapeInstaller):
    def install(self):
        # Implementing Linux-specific installation logic
        inkscape_url = "https://inkscape.org/gallery/item/44615/inkscape-1.3.2.tar.xz"
        home_path = str(Path.home())
        source_path = Path(home_path) / "inkscape_source"
        install_path = self.install_path

        # Download Inkscape
        print("Downloading Inkscape for Linux...")
        response = requests.get(inkscape_url, stream=True)
        if response.status_code == 200:
            with open(source_path / "inkscape.tar.xz", 'wb') as f:
                f.write(response.content)
            print("Download completed.")

            # Extracting and installing Inkscape
            print("Installing Inkscape...")
            subprocess.run(["tar", "-xf", str(source_path / "inkscape.tar.xz"), "-C", str(source_path)], check=True)
            build_path = source_path / "build"
            os.makedirs(build_path, exist_ok=True)
            os.chdir(build_path)
            subprocess.run(["cmake", "..", "-DCMAKE_INSTALL_PREFIX=" + str(install_path)], check=True)
            subprocess.run(["make"], check=True)
            subprocess.run(["make", "install"], check=True)
            print("Inkscape installed successfully.")
        else:
            print("Failed to download Inkscape.")

class InkscapeInstallerFactory:
    @staticmethod
    def get_installer():
        if platform.system() == 'Windows':
            return WindowsInkscapeInstaller()
        elif platform.system() == 'Darwin':  # macOS
            return MacOSInkscapeInstaller()
        elif platform.system() == 'Linux':
            return LinuxInkscapeInstaller()
        else:
            raise NotImplementedError("Unsupported operating system")


class InkscapeInstaller(ABC):
    def __init__(self):
        self.install_path = Path.home() / ".md3d/inkscape"
        self.binary = None
        self.install_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def install(self):
        """Install Inkscape."""
        pass

    def is_installed(self):
        """Check if Inkscape is already installed."""
        return self.install_path.exists()

class CustomHtmlFormatter(HtmlFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def download_images_from_markdown(md_content, base_dir):
    image_links = []
    lines = md_content.split('\n')
    for line in lines:
        if line.startswith('![') and '](' in line and line.endswith(')'):
            link_start = line.find('](') + 2
            link_end = line.find(')', link_start)
            image_link = line[link_start:link_end]
            image_links.append(image_link)
            # remove the image link from the line
            lines.remove(line)

    image_paths = []
    for link in image_links:
        if link.startswith('http'):
            try:
                response = requests.get(link)
                if response.status_code == 200:
                    img_data = response.content
                    img_name = os.path.basename(urlparse(link).path)
                    img_path = base_dir / img_name
            except requests.exceptions as e:
                raise(f"Error downloading image: {e}")
        else:
            try:
                img_path = Path(link)
                img_name = img_path.name
                img_data = img_path.read_bytes()
            except FileNotFoundError as e:
                raise(f"Error reading image: {e}")
        with open(img_path, 'wb') as f:
            f.write(img_data)
        image_paths.append(str(img_path))

    print(f"Image paths: {image_paths}")

    cleaned_md_content = '\n'.join(lines)

    return image_paths, cleaned_md_content

# Function to import images into Blender and position them
# def import_and_position_images(image_paths, offset_x=4.5, offset_y=-0.01, offset_z=2.8):
#     for i, img_path in enumerate(image_paths):
#         # Load image
#         with Image.open(img_path) as img:
#             img_data = io.BytesIO()
#             img.save(img_data, format='PNG')
#             img_data.seek(0)

#         # Create image data block in Blender
#         img_name = os.path.basename(img_path)
#         blender_img = bpy.data.images.load(img_path, check_existing=True)
#         blender_img.pack()

#         # Create a new plane and assign the image as a texture
#         bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD')
#         plane = bpy.context.active_object
#         plane.rotation_euler[0] = 1.5708  # 90 degrees in radians
    
#         plane.location.x = i * offset_x
#         plane.location.y = offset_y
#         plane.location.z = offset_z

#         # Create material with image texture
#         mat = bpy.data.materials.new(name=img_name + '_Mat')
#         mat.use_nodes = True
#         # bsdf = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
#         bsdf = mat.node_tree.nodes['Principled BSDF']
#         bsdf.inputs['Roughness'].default_value = 0.1
#         tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
#         tex_image.image = blender_img
#         mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
#         plane.data.materials.append(mat)

#         # Adjust plane size to match image aspect ratio
#         img_aspect = img.width / img.height
#         plane.scale.x = img_aspect

def import_and_position_images(image_paths, offset_x = 2.0, offset_y=-0.05, offset_z=2.8, text_plane_width=2):
    for i, img_path in enumerate(image_paths):
        # Load image
        with Image.open(img_path) as img:
            img_data = io.BytesIO()
            img.save(img_data, format='PNG')
            img_data.seek(0)

        # Create image data block in Blender
        img_name = os.path.basename(img_path)
        blender_img = bpy.data.images.load(img_path, check_existing=True)
        blender_img.pack()

        # Create a new plane and assign the image as a texture
        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, align='WORLD')
        plane = bpy.context.active_object
        plane.rotation_euler[0] = 1.5708  # 90 degrees in radians
    
        # Adjust plane size to match image aspect ratio
        img_aspect = img.width / img.height
        plane.scale.x = img_aspect

        # Calculate X-coordinate for right alignment
        # The center position of the text plane
        text_plane_center_x = i * text_plane_width
        # The right edge of the text plane
        right_edge_text_plane = text_plane_center_x + (text_plane_width / 2)
        # Position the image plane so its right edge aligns with the right edge of the text plane
        plane.location.x = right_edge_text_plane - (plane.dimensions.x / 2) + i / plane.scale.x 
        plane.location.y = offset_y
        plane.location.z = offset_z

        # Create material with image texture
        mat = bpy.data.materials.new(name=img_name + '_Mat')
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Roughness'].default_value = 1.0
        bsdf.inputs['Metallic'].default_value = 0.6
        tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image.image = blender_img
        mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
        plane.data.materials.append(mat)

        # create the images collection if it doesn't exist
        if 'Images' not in bpy.data.collections:
            bpy.data.collections.new('Images')
            bpy.context.scene.collection.children.link(bpy.data.collections['Images'])
        # move plane to the images collection
        bpy.data.collections['Images'].objects.link(plane)
        # name the plane image i
        plane.name = f"Image {i}"

def markdown_to_html(md_text):
    print ("Converting Markdown to HTML...")
    print (md_text)
    # Create an instance of HtmlFormatter
    formatter = CustomHtmlFormatter(style="default")  # You can change the style as needed
    css = formatter.get_style_defs('.codehilite')

    # Create an instance of CodeHiliteExtension with the formatter
    code_hilite_extension = CodeHiliteExtension(pygments_formatter=formatter)
    code_hilite_extension = CodeHiliteExtension()

    # Convert Markdown to HTML
    md_extensions = ["fenced_code", code_hilite_extension]
    html_content = markdown.markdown(md_text, extensions=md_extensions)

    # Combine CSS and HTML
    full_html = f"<html><head><style>{css}</style></head><body>{html_content}</body></html>"
    with open("test.html", "w") as f:
        f.write(full_html)
    
    return full_html


def convert_md_to_pdf(md_text, output_pdf):
    html = markdown_to_html(md_text)
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
    page.insert_htmlbox(rect, html)
    doc.save(output_pdf)
    doc.close()


def convert_pdf_to_svg(input_pdf, output_svg):
    try:
        # For Inkscape 1.0 and later
        subprocess.run([
            str(inkscape.binary), 
            input_pdf, 
            "--export-type=svg", 
            "--export-filename=" + output_svg
        ], check=True)
    except subprocess.CalledProcessError as e:
        print("An error occurred: ", e)

def split_markdown(md_content):
    return md_content.split('---')

def convert_to_svgs(md_sections, base_dir):
    svg_filenames = []
    for i, section in enumerate(md_sections):
        output_pdf = base_dir / f'section_{i}.pdf'
        output_svg = base_dir / f'section_{i}.svg'
        convert_md_to_pdf(section, str(output_pdf))
        convert_pdf_to_svg(str(output_pdf), str(output_svg))
        svg_filenames.append(str(output_svg))
    return svg_filenames

def create_material(name='Slides', roughness = 0.234, alpha = 0.630, base_color = (0.8, 0.8, 0.8, 1.0)):
    """Create a material for the slides."""
    bpy.data.materials.new(name=name)

    bpy.data.materials[name].use_nodes = True

    bsdf = bpy.data.materials[name].node_tree.nodes['Principled BSDF']
    
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Base Color'].default_value = base_color
    
    bsdf.inputs['Alpha'].default_value = alpha
    bsdf.inputs['Transmission Weight'].default_value = 0.6

def import_and_transform_svgs(svg_files, offset_x=3):
    existing_objects = []
    for obj in bpy.data.objects:
        existing_objects.append(obj)

    for i, svg_file in enumerate(svg_files):
        # add a plane as a background for the text
        create_plane = bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=True, align='WORLD')
        bpy.ops.transform.resize(value=(2, 1, 1))
        bpy.ops.transform.translate(value=(0, 2.8, 0))
        bpy.ops.object.editmode_toggle()
        plane = bpy.context.active_object
        plane.data.materials.append(bpy.data.materials['Slides'])

        # name the plane Slide i
        plane.name = f"Slide {i}"

        # apply scale


        
        # Import SVG
        bpy.ops.import_curve.svg(filepath=svg_file)
        new_objects = []

        print(f"Existing objects: {existing_objects}")

        for obj in bpy.data.objects:
            if obj not in existing_objects:
                new_objects.append(obj)
                existing_objects.append(obj)

        print(f"New objects: {new_objects}")
        

        for obj in new_objects:
            print(f"Imported object: {i}  {obj.name}")

            obj.rotation_euler[0] = 1.5708  # 90 degrees in radians
            
            obj.modifiers.new(name='Solidify', type='SOLIDIFY')

            
            obj.modifiers['Solidify'].offset = 0.0

        

            # apply scale but not for the plane
            if 'Slide' not in obj.name:
                obj.scale = (10, 10, 10)
                obj.location.x = (i * offset_x) - 0.9
                obj.location.z = obj.location.z + 0.15
                obj.location.y = obj.location.y - 0.05
                obj.modifiers['Solidify'].thickness = 0.0010
            else:
                obj.location.x = i * offset_x
                obj.modifiers['Solidify'].thickness = 0.02
          
        

            # insert keyframe in camera for location
            bpy.context.scene.frame_set(i+1)
            bpy.context.scene.camera.location.x = offset_x * i
            bpy.context.scene.camera.keyframe_insert(data_path='location', index=-1)


def save_blend_file(filename):
    bpy.ops.wm.save_as_mainfile(filepath=filename)

inkscape = InkscapeInstallerFactory.get_installer()

def main(input_md: str):
    # Determine the OS and create the appropriate installer

    # Check if Inkscape is installed
    if not inkscape.is_installed():
        inkscape.install()

    base_dir = Path.home() / ".md3d" / "documents"
    base_dir.mkdir(parents=True, exist_ok=True)

    input_md_file = Path(input_md)
    input_md_content = input_md_file.read_text()

    base_dir = Path.home() / ".md3d" / "images"
    base_dir.mkdir(parents=True, exist_ok=True)
    image_paths, cleaned_md_content = download_images_from_markdown(input_md_content, base_dir)

    
    markdown_sections = split_markdown(cleaned_md_content)
    svg_files = convert_to_svgs(markdown_sections, base_dir)


    
    # remove the default cube
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    # create a material for the slides
    create_material()

    import_and_position_images(image_paths)

    # add camera
    bpy.ops.object.camera_add()
    bpy.context.scene.camera = bpy.data.objects['Camera']
    bpy.context.scene.camera.location = (0, -6.5, 3)
    bpy.context.scene.camera.rotation_euler = (1.5708, 0, 0)


    import_and_transform_svgs(svg_files)

    bpy.context.scene.frame_set(1)

    # area: Sequence[area] = None
    # region: bpy.types.RegionView3D = None
    # region.view_camera_zoom
    # region.view_rotation

 
    
    # set camera to active
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    print(f"camera {space.region_3d.view_perspective}")
                    # space.region_3d.view_perspective = 'CAMERA'
                    # space.region_3d.view_perspective = 'ORTHO'
                    # space.region_3d.view_camera_zoom = 1.5
                    # # space.region_3d.view_perspective = 'PERSP'
                    # print(f"camera zoom {space.region_3d.view_camera_zoom}")
                    # Set the view rotation (Euler angles in radians: X, Y, Z)
                    space.region_3d.view_rotation = Euler((math.radians(90), math.radians(0), math.radians(0)), 'XYZ').to_quaternion()
                    space.region_3d.view_location = Vector((0, -2, 3))
                    area.spaces[0].shading.type = "MATERIAL"

                
                    zoom_level = 2.0  # Example zoom level
                 

                    # Set the zoom level
                    space.region_3d.view_distance = zoom_level

    # create a backdrop as wide as the number of slides
    backdrop_width = len(svg_files) * 6

    # import backdrop glb
    bpy.ops.import_scene.gltf(filepath=str(Path(__file__).parent / "backdrop.glb"))

    bpy.ops.object.editmode_toggle()




    # Ensure in object mode first
    

    # Assuming backdrop is the active object and it's a plane aligned along X and Y axes
    bpy.ops.object.mode_set(mode='OBJECT')
    backdrop = bpy.context.active_object
    backdrop_height = 10
   
    backdrop.scale.x = backdrop_width
    backdrop.scale.y = backdrop_height
    backdrop.scale.z = backdrop_height
    backdrop.location.x = (backdrop_width / 2) - 0.5
    bpy.ops.object.mode_set(mode='EDIT')

    create_material(name='Backdrop', roughness = 0.9, alpha = 0.630, base_color = (0.8, 0.8, 0.8, 1.0))
    backdrop.data.materials.append(bpy.data.materials['Backdrop'])

    bpy.ops.object.mode_set(mode='OBJECT')

  


    save_blend_file(input_md_file.stem + '.blend')

    print(f"Conversion complete. Blend file saved as: {input_md_file.stem}.blend")

if __name__ == "__main__":
    typer.run(main)
