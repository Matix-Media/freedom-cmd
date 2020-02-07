import psutil
import sys
import json
import datetime
import platform
import os.path
import subprocess
import ntpath
import requests


class Commands():
    def __init__(self):
        self.platform = platform.system()
        self.plt_rls = platform.release()

    def cmd_check_for_observers(self):
        observers = []
        observers_settings = {}

        print("Reading observers data...")
        try:
            with open('settings.json') as json_file:
                tmp_json = json.load(json_file)
                observers = tmp_json["observers"]
                observers_settings = tmp_json["settings"]["check_for_observers"]
        except OSError:
            print("Error reading observers. Exiting...")
            exit(1)

        processes = []

        # Iterate over all running process
        print("Done. Getting all processes...")
        for proc in psutil.process_iter():
            try:
                # Get process name & pid from process object.
                processName = proc.name()
                processID = proc.pid
                processes.append({"name": processName, "ID": processID})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                print("Error getting Processes. Continuing")

        active_observers = []

        # Iterate over all found processes to check for observer
        print("Done. Checking processes for observers...")
        for process in processes:
            if process["name"] in observers:
                process["detection_time"] = str(datetime.datetime.now())
                active_observers.append(process)

        if observers_settings["write_to_output"]:
            print("Done. Writing to output file ('{0}')...".format(observers_settings["output_file"]))
            try:
                with open(observers_settings["output_file"], "w") as f:
                    for act_obs in active_observers:
                        f.write(act_obs["detection_time"] + " ::: " + act_obs["name"] + " ::: " + str(act_obs["ID"]) + "\n")
            except OSError:
                print("Error writing output file. Continuing")
        else:
            print("Done.")

        # Print out possible observers
        if len(active_observers) > 0:
            print("\nPossible observers:")
            for act_obs in active_observers:
                print("     >", act_obs["name"], ":::", act_obs["ID"], ":::", act_obs["detection_time"])
        else:
            print("No possible observers found.")

    def cmd_start_tor(self):
        # Read settings
        tor_settings = {}
        print("Reading tor settings...")
        try:
            with open('settings.json') as json_file:
                tmp_json = json.load(json_file)
                tor_settings = tmp_json["settings"]["tor"]
        except OSError:
            print("Error reading tor settings. Exiting...")
            exit(1)

        print("Done.")

        # Functions
        def download_file(url, save_file):
            link = url
            file_name = save_file
            with open(file_name, "wb") as f:
                print("Downloading %s" % link)
                response = requests.get(link, stream=True)
                total_length = response.headers.get('content-length')

                if total_length is None:  # no content length header
                    f.write(response.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        done = int(50 * dl / total_length)
                        sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                        sys.stdout.flush()

        def get_os_ext(os):
            if os == "Windows":
                return "exe"
            if os == "Darwin":
                return "dmg"
            if os == "Linux":
                return "tar.xz"
            return ""

        def start_tor():
            inst_path = None
            if self.platform == "Windows":
                inst_path = "\"%s\"" % os.path.abspath("%s/%s/Browser/firefox.exe" % (tor_settings["installation-path"], self.platform))
            if self.platform == "Darwin":
                inst_path = "open -a tor"
            if self.platform == "Linux":
                tor_inst_path = os.path.join(tor_settings["installation-path"], "/tor-browser_en-US/start-tor-browser")
                inst_path = "\"%s\"" % os.path.abspath(tor_inst_path)
            print("Starting tor browser...")
            process = subprocess.Popen(inst_path, stdout=subprocess.PIPE)
            print("tor browser started.")
            process.wait()
            print("tor browser closed.")

        def install_tor():
            os_ext = get_os_ext(self.platform)
            inst_path = os.path.abspath("%s/%s" % (tor_settings["installation-path"], self.platform))
            instlr_path = os.path.abspath("./data/tor/installers/tor-%s.%s" % (self.platform, os_ext))
            instlr_silent = " /S"
            instlr_command = None

            if tor_settings["run_instlr_silent"]:
                instlr_silent = " /S"
            else:
                instlr_silent = ""

            if not os.path.isfile(instlr_path):
                print("Tor browser installer not found. Downloading.")
                download_file(tor_settings["installer-urls"][self.platform], instlr_path)
                print("Download done.")

            if os.path.isfile(instlr_path):
                print("\nPlease wait while tor browser is installing. This process can take up to several minutes.\n...")
                if self.platform == "Windows":
                    instlr_command = "\"%s\" %s /D=%s" % (instlr_path, instlr_silent, inst_path)
                if self.platform == "Darwin":
                    instlr_command = "sudo hdiutil attach \"%s\" && sudo installer -package /Volumes/tor-Darwin/tor-Darwin.pkg -target \"%s\" && sudo hdiutil detach /Volumes/tor-Darwin" % (instlr_path, inst_path)
                if self.platform == "Linux":
                    instlr_command = "sudo apt install xz-utils && tar --xvf \"%s\" -C \"%s\"" % (instlr_path, inst_path)
                process = subprocess.Popen(instlr_command, stdout=subprocess.PIPE)
                process.wait()
                rtn_code = process.returncode
                if rtn_code == 0:
                    print("Installation complete.")
                    return 0
                else:
                    print("Installation canceled.")
                    return 1
            else:
                print("Installer not found. Please try to install tor manually.")

        def check_for_tor():
            inst_path = os.path.abspath("%s/%s" % (tor_settings["installation-path"], self.platform))
            if os.path.isdir(inst_path):
                start_tor()
            else:
                print("Tor browser installation not found. Installing tor browser.")
                if install_tor() == 0:
                    print("Successfully installed tar browser.\n\n")
                    start_tor()
                else:
                    print("Exiting")
                    exit(1)

        # Run
        check_for_tor()


# Command control
cmd = Commands()
commands = {"check_for_observers": cmd.cmd_check_for_observers, "start_tor": cmd.cmd_start_tor}

if len(sys.argv) > 1:
    if sys.argv[1] in commands:
        if len(sys.argv) > 2:
            commands[sys.argv[1]](sys.argv[2:])
        else:
            commands[sys.argv[1]]()
    else:
        print("The command was not found.")
else:
    print("No command given.")
