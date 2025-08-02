from flask import Flask, make_response, request
from config import Config
from controller.controller import Controller, Jobs
import json
import os
import logging
import requests
from packaging.version import Version
import pytesseract
import threading


class Server:
    def __init__(self):
        self.app = Flask(__name__)

        self.UPLOAD_FOLDER = 'input'
        if not os.path.exists(self.UPLOAD_FOLDER):
            os.makedirs(self.UPLOAD_FOLDER)

        self.app.config['UPLOAD_FOLDER'] = self.UPLOAD_FOLDER
        self.config = Config()
        self.controller = Controller()
        self.gui = ServerGUI()

        self.controller.register_gui(self.gui)

        self.app.add_url_rule('/version', 'get_version', self.get_version)
        self.app.add_url_rule('/theme', 'theme', self.theme, methods=['GET', 'POST'])
        self.app.add_url_rule('/checkForUpdate', 'check_for_update', self.gui.check_for_update)
        self.app.add_url_rule('/userLanguages', 'get_languages', self.get_languages)
        self.app.add_url_rule('/isoCodes', 'get_iso_codes', self.get_iso_codes)
        self.app.add_url_rule('/upload', 'upload_file', self.upload_file, methods=['POST'])
        self.app.add_url_rule('/convert', 'convert', self.convert, methods=['POST'])
        self.app.add_url_rule('/userSettings', 'user_settings', self.user_settings, methods=['GET', 'POST'])
        self.app.add_url_rule('/files', 'video_files', self.video_files)
        self.app.add_url_rule('/conversionStatus', 'update_gui', self.gui.update_gui, methods=['GET', 'POST'])
        self.app.add_url_rule('/cancelConversion', 'cancel_conversion', self.cancel_conversion, methods=['POST'])

    def get_version(self):
        response = make_response(self.config.get_version(), 200)
        response.mimetype = "text/plain"
        return response

    # TODO: remove in favor of userSettings
    def theme(self):
        if request.method == 'GET':
            response = make_response(self.config.get_theme(), 200)
            response.mimetype = "text/plain"
            return response
        else:
            # Assuming the theme is in plain text format
            theme = request.data.decode('utf-8')
            settings = {
                Config.Settings.THEME: theme
            }
            print(f"Setting theme to: {theme}")
            self.config.save_settings(settings)
            self.config.save_config()
            return make_response("Theme updated successfully", 200)  # Add this line

    def get_languages(self):
        languages = pytesseract.get_languages()
        return make_response(json.dumps(languages), 200, {'Content-Type': 'application/json'})

    def get_iso_codes(self):
        iso_codes = open('gui/web/scripts/iso_codes.txt').readlines()
        iso_codes = [line.removesuffix('\n') for line in iso_codes]
        return make_response(json.dumps(iso_codes), 200, {'Content-Type': 'application/json'})

    def upload_file(self):
        if 'file' not in request.files:
            return make_response("No file part", 400)
        file = request.files['file']
        if file.filename == '':
            return make_response("No selected file", 400)
        if file:
            filename = file.filename
            file.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
            return make_response("File uploaded successfully", 200)

    def convert(self):
        data = json.loads(request.data)
        if not data:
            return make_response("No data provided", 400)

        files = data.get('files', [])
        sub_format = data.get('format', 'SubRip Text (.srt)')
        brightness = data.get('brightness', 0)
        brightness = int(brightness)
        edit_before_muxing = data.get('edit', False)
        save_pgs_images = data.get('saveImages', False)
        keep_original_mkv = data.get('keepFiles', False)
        keep_copy_old = data.get('keepOldSubs', False)
        keep_copy_new = data.get('keepNewSubs', False)
        use_different_languages = data.get('useDiffLang', False)
        different_languages = data.get('diffLangs', [])
        different_languages = [
            f'{lang['from']} -> {lang['to']}' for lang in different_languages
        ] if use_different_languages else []

        different_languages = '\n'.join(different_languages)

        files = [os.path.join(self.app.config['UPLOAD_FOLDER'], file) for file in files]

        values = {
            'selected_paths': files,
            'edit_subs': edit_before_muxing,
            'save_images': save_pgs_images,
            'keep_old_mkvs': keep_original_mkv,
            'keep_old_subs': keep_copy_old,
            'keep_new_subs': keep_copy_new,
            'diff_langs': different_languages,
            'sub_format': sub_format,
            'brightness_diff': brightness
        }

        self.controller.gui_send_values(0, values)
        threading.Thread(target=self.controller.start_subconverter, daemon=True).start()
        
        response = json.dumps({
            'success': True
        })
        return make_response(response, 200, {'Content-Type': 'application/json'})

    def user_settings(self):
        if request.method == 'GET':
            settings = self.config.get_json()
            response = make_response(json.dumps(settings), 200, {'Content-Type': 'application/json'})
            return response
        else:
            print(type(request.json))
            self.config.from_json(request.json)
            return make_response("Settings updated successfully", 200)
        
    def build_tree(self, root_dir):
        tree = {}
        for entry in os.scandir(root_dir):
            if entry.is_file():
                tree[entry.name] = {
                    'size': os.path.getsize(entry.path),
                    'path': entry.path
                }
            elif entry.is_dir():
                tree[entry.name] = self.build_tree(entry.path)
        return tree

    def video_files(self):
        # iterate over UPLOAD_FOLDER and put all files with the size in a json dir. Keep the dir structure.
        files = self.build_tree(self.app.config['UPLOAD_FOLDER'])
        response = make_response(json.dumps(files), 200, {'Content-Type': 'application/json'})
        return response
    
    def cancel_conversion(self):
        """Cancel the current conversion process."""
        self.gui.continue_flag = False
        self.gui.edit_flag = False
        self.gui.stop_flag = True
        logging.info("Conversion cancelled by user.")
        
        response = make_response("Conversion cancelled", 200)
        return response
    

class ServerGUI:
    def __init__(self):
        self.conversion_status = {}
        self.continue_flag = None
        self.edit_flag = None
        self.stop_flag = None
        self.config = Config()

    def check_for_update(self):
        logging.info("Checking for updates.")

        try:
            response = requests.get("https://api.github.com/repos/Kleeraphie/MKV-Subtitle-Converter/releases/latest")
            latest_version = response.json()["tag_name"]

            update_available = Version(latest_version) > Version(self.config.get_version())
        except: # if there is no internet connection or the request fails
            update_available = False

        response = {
            'updateAvailable': update_available,
            'latestVersion': latest_version if update_available else None
        }
        return make_response(json.dumps(response), 200, {'Content-Type': 'application/json'})

    def update(self, file_counter, finished_files_counter, files_with_error_counter, job, sc_error_code, sc_error_msg, sc_edit_flag, sc_sub_dir):
            """Update the GUI while the subconverter is running"""

            self.conversion_status['file_counter'] = file_counter
            self.conversion_status['finished_files_counter'] = finished_files_counter
            self.conversion_status['files_with_error_counter'] = files_with_error_counter
            self.conversion_status['job'] = job.value
            self.conversion_status['job_progress'] = Jobs.get_percentage(job)
            self.conversion_status['sc_error_code'] = sc_error_code
            self.conversion_status['sc_error_msg'] = sc_error_msg
            self.conversion_status['sc_edit_flag'] = sc_edit_flag
            self.conversion_status['sc_sub_dir'] = 'output'

            # if sc_error_code != 0:
            #     self.window.bell()
            #     self.continue_flag = tk.messagebox.askyesno(self.translate("Error"), self.translate("Error #{error_code}: {error}\nDo you want to continue with the next file?").format(error_code=sc_error_code, error=sc_error_msg))
            # if sc_edit_flag:
            #     tk.messagebox.showinfo(self.translate("Edit subtitles"), self.translate("The subtitles are ready for editing. They can be found at {sub_dir}. Press OK when you are done.").format(sub_dir=sc_sub_dir))
            #     self.edit_flag = False


    def update_gui(self):
        response = make_response(json.dumps(self.conversion_status), 200, {'Content-Type': 'application/json'})
        return response
    
    def get_stop_flag(self):
        return self.stop_flag
    
    def show_progress(self):
        pass

    def hide_progress(self):
        pass

    def show_finish_dialog(self):
        pass

if __name__ == '__main__':
    server = Server()
    # Repeat for other routes: theme, check_for_update, etc.
    server.app.run(host='0.0.0.0', port=5000, debug=True)
