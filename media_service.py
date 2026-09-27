import os
import uuid
import time
try:
    from werkzeug.utils import secure_filename
except ImportError:
    import re
    import unicodedata

    def secure_filename(filename):
        """Fallback secure_filename implementation if werkzeug is not installed."""
        if not filename:
            return ""
        if isinstance(filename, str):
            filename = unicodedata.normalize('NFKD', filename)
        filename = re.sub(r'[^A-Za-z0-9_.-]', '_', filename)
        return filename.strip('._')

# Cloudinary Configuration & Integration
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    cloudinary = None
    CLOUDINARY_AVAILABLE = False

# Media upload storage configurations
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
CHATROOM_UPLOAD_FOLDER = os.environ.get('CHATROOM_UPLOAD_FOLDER', 'static/chatroom_uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


def configure_cloudinary():
    """
    Configures Cloudinary using environment variables if available.
    Supports either CLOUDINARY_URL or (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET).
    Returns True if successfully configured, False otherwise.
    """
    if not CLOUDINARY_AVAILABLE:
        return False

    cloudinary_url = os.environ.get('CLOUDINARY_URL')
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    if cloudinary_url:
        cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
        return True
    elif cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True
    return False


# Initialize Cloudinary at module load
CLOUDINARY_INITIALIZED = configure_cloudinary()


def is_cloudinary_active():
    """Returns True if Cloudinary is installed and configured with credentials."""
    return CLOUDINARY_AVAILABLE and (
        bool(os.environ.get('CLOUDINARY_URL')) or
        bool(os.environ.get('CLOUDINARY_CLOUD_NAME') and os.environ.get('CLOUDINARY_API_KEY') and os.environ.get('CLOUDINARY_API_SECRET'))
    )


def ensure_upload_dirs(upload_folder=UPLOAD_FOLDER, chatroom_upload_folder=CHATROOM_UPLOAD_FOLDER):
    """Ensures local storage directories exist."""
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
    if chatroom_upload_folder:
        os.makedirs(chatroom_upload_folder, exist_ok=True)


def allowed_file(filename, allowed_extensions=None):
    """Checks whether the filename has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = allowed_extensions if allowed_extensions is not None else ALLOWED_EXTENSIONS
    return ext in allowed


def upload_to_cloudinary(file_obj_or_path, folder=None, public_id=None, resource_type="auto"):
    """
    Uploads a media file or path to Cloudinary.
    Returns the secure URL on success, or None on failure.
    """
    if not CLOUDINARY_AVAILABLE:
        print("Cloudinary package is not installed.")
        return None
    try:
        options = {
            'resource_type': resource_type,
            'secure': True
        }
        if folder:
            options['folder'] = folder
        if public_id:
            options['public_id'] = public_id

        response = cloudinary.uploader.upload(file_obj_or_path, **options)
        return response.get('secure_url') or response.get('url')
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None


def save_media_file(file, target_folder=UPLOAD_FOLDER, filename_prefix="", custom_filename=None, prefer_cloudinary=True, leading_slash=True):
    """
    Saves or uploads a media file.
    If prefer_cloudinary is True and Cloudinary is configured, uploads to Cloudinary and returns URL.
    Otherwise, securely saves to target_folder locally and returns the web-accessible path.
    """
    if not file or not getattr(file, 'filename', None) or file.filename == '':
        return None

    # Optional Cloudinary upload
    if prefer_cloudinary and is_cloudinary_active():
        cloud_folder = os.path.basename(target_folder) if target_folder else "uploads"
        url = upload_to_cloudinary(file, folder=cloud_folder)
        if url:
            return url

    # Local file saving fallback
    ensure_upload_dirs(upload_folder=target_folder, chatroom_upload_folder=None)
    base_name = secure_filename(file.filename) if getattr(file, 'filename', None) else "file"
    if custom_filename:
        parts = custom_filename.replace('\\', '/').split('/')
        filename = '/'.join(secure_filename(p) for p in parts if p)
    elif filename_prefix:
        filename = f"{filename_prefix}_{base_name}"
    else:
        filename = base_name

    save_path = os.path.join(target_folder, filename)
    sub_dir = os.path.dirname(save_path)
    if sub_dir:
        os.makedirs(sub_dir, exist_ok=True)
    file.save(save_path)

    # Return web-accessible path
    norm_folder = target_folder.replace('\\', '/').strip('/')
    norm_file = filename.replace('\\', '/').lstrip('/')
    rel_path = f"{norm_folder}/{norm_file}"
    if leading_slash:
        return f"/{rel_path}"
    return rel_path
