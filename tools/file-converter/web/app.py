"""Flask web application for file converter."""

import json
import os
import sys
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF for PDF preview

web_dir = os.path.dirname(os.path.abspath(__file__))
sys_path = os.path.dirname(os.path.dirname(web_dir))
sys.path.insert(0, sys_path)

from file_converter.server import FileConverter

app = Flask(__name__, template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'converter_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

converter = FileConverter()

jobs = {}


def allowed_file(filename, allowed_exts):
    return '.' in filename and os.path.splitext(filename)[1].lower() in allowed_exts


@app.route('/')
def index():
    return render_template('index.html', config=config)


@app.route('/api/merge', methods=['POST'])
def merge_files():
    job_id = uuid.uuid4().hex[:8]

    file_type = request.form.get('file_type', 'pdf')
    output_format = request.form.get('output_format', 'pdf')
    layout = request.form.get('layout', 'single')

    files = request.files.getlist('files')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': 'No files uploaded'}), 400

    temp_dir = os.path.join(app.root_path, '..', 'output', 'temp', job_id)
    os.makedirs(temp_dir, exist_ok=True)

    saved_paths = []
    if file_type == 'pdf':
        allowed_exts = {'.pdf'}
        for f in files:
            if f.filename and allowed_file(f.filename, allowed_exts):
                filename = secure_filename(f.filename)
                # Ensure unique filename
                base, ext = os.path.splitext(filename)
                counter = 1
                filepath = os.path.join(temp_dir, filename)
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(temp_dir, filename)
                    counter += 1
                f.save(filepath)
                saved_paths.append(filepath)
    else:
        allowed_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
        for f in files:
            if f.filename and allowed_file(f.filename, allowed_exts):
                filename = secure_filename(f.filename)
                # Ensure unique filename
                base, ext = os.path.splitext(filename)
                counter = 1
                filepath = os.path.join(temp_dir, filename)
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(temp_dir, filename)
                    counter += 1
                f.save(filepath)
                saved_paths.append(filepath)

    if not saved_paths:
        return jsonify({'success': False, 'error': 'No valid files found'}), 400

    try:
        if file_type == 'pdf':
            result = converter.merge_pdfs(saved_paths)
        elif output_format == 'jpg':
            result = converter.merge_images_to_jpg(saved_paths)
        else:
            result = converter.merge_images_to_pdf(saved_paths, layout=layout)

        # Add output_filename to result for consistency
        if 'output_filename' not in result:
            result['output_filename'] = os.path.basename(result.get('output_path', 'merged.pdf'))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        for path in saved_paths:
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

    jobs[job_id] = {
        'status': 'completed',
        'result': result
    }

    result['job_id'] = job_id
    return jsonify(result)


@app.route('/api/status/<job_id>')
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    return jsonify(jobs[job_id])


@app.route('/api/preview/<job_id>')
def preview_file(job_id):
    """Generate preview image for merged PDF or image."""
    if job_id not in jobs:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed'}), 400

    result = job['result']
    output_path = result.get('output_path')

    if not output_path or not os.path.exists(output_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    filename = os.path.basename(output_path).lower()

    try:
        if filename.endswith('.pdf'):
            # Convert first page of PDF to image using PyMuPDF
            doc = fitz.open(output_path)
            if doc.page_count > 0:
                page = doc[0]
                mat = fitz.Matrix(1.5, 1.5)  # Scale 1.5x
                pix = page.get_pixmap(matrix=mat)
                preview_path = output_path.replace('.pdf', '_preview.png')
                pix.save(preview_path)
                doc.close()
                return send_file(preview_path, mimetype='image/png')
            doc.close()
        else:
            # Return image as-is for JPG/PNG previews
            mimetype = 'image/jpeg' if filename.endswith('.jpg') else 'image/png'
            return send_file(output_path, mimetype=mimetype)

        return jsonify({'success': False, 'error': 'Preview generation failed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download/<job_id>')
def download_file(job_id):
    if job_id not in jobs:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'success': False, 'error': 'Job not completed'}), 400

    result = job['result']
    output_path = result.get('output_path')

    if not output_path or not os.path.exists(output_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    filename = os.path.basename(output_path)
    return send_file(output_path, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(host=config['host'], port=config['port'], debug=True)