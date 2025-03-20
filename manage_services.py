import subprocess
import os

class ServiceManager:
    def __init__(self):
        self.service_file_directory = "/etc/systemd/system"

    def check_service_exists(self, service_name):
        """
        Checks if a service exists using systemctl.

        Args:
            service_name: The name of the service to check.
        """
        try:
            service_file_path = os.path.join(self.service_file_directory, f"{service_name}.service")
            if os.path.isfile(service_file_path):
                return True, f"Service '{service_name}' exists."
            else:
                return False, f"Service '{service_name}' does not exist."
        except subprocess.CalledProcessError as e:
            print("service does not exist")
            return False, f"Service '{service_name}' does not exist. Standard Error: {e.stderr}"

    def create_service(self, service_name, service_content):
        """
        Creates a service file and enables it using systemctl.

        Args:
            service_name: The name of the service to create.
            service_content: The content of the service file as a string.
        """
        service_file_path = os.path.join(self.service_file_directory, f"{service_name}.service")
        try:
            subprocess.run(["sudo", "tee", service_file_path], input=service_content.encode(), check=True)
            self.enable_service(service_name)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            self.start_service(service_name)
            return True, f"Service file '{service_file_path}' created."
        except subprocess.CalledProcessError as e:
            return False, f"Error creating service '{service_name}': {e}. Standard Error: {e.stderr}"
        
    def check_enabled(self, service_name):
        """
        Checks if a service is enabled using systemctl.

        Args:
            service_name: The name of the service to check.
        """
        try:
            subprocess.run(["sudo","systemctl", "is-enabled", service_name], check=True)
            return True, f"Service '{service_name}' is enabled."
        except subprocess.CalledProcessError as e:
            return False, f"Service '{service_name}' is not enabled. Standard Error: {e.stderr}"

    def enable_service(self, service_name):
        """
        Enables a service using systemctl.

        Args:
            service_name: The name of the service to enable.
        """
        try:
            subprocess.run(["sudo", "systemctl", "enable", service_name], check=True)
            return True, f"Service '{service_name}' enabled."
        except subprocess.CalledProcessError as e:
            return False, f"Error enabling service '{service_name}': {e}. Standard Error: {e.stderr}"

    def start_service(self, service_name):
        """
        Starts a service using systemctl.

        Args:
            service_name: The name of the service to start.
        """
        try:
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "start", service_name], check=True)
            return True, f"Service '{service_name}' started."
        except subprocess.CalledProcessError as e:
            return False, f"Error starting service '{service_name}': {e}. Standard Error: {e.stderr}"
    def check_running(self, service_name):
        """
        Checks if a service is running using systemctl.

        Args:
            service_name: The name of the service to check.
        """
        try:
            subprocess.run(["sudo", "systemctl", "is-active", service_name], check=True)
            return True, f"Service '{service_name}' is running."
        except subprocess.CalledProcessError as e:
            return False, f"Service '{service_name}' is not running. Standard Error: {e.stderr}"

    def stop_service(self, service_name):
        """
        Stops a service using systemctl.

        Args:
            service_name: The name of the service to stop.
        """
        try:
            subprocess.run(["sudo", "systemctl", "stop", service_name], check=True)
            return True, f"Service '{service_name}' stopped."
        except subprocess.CalledProcessError as e:
            return False, f"Error stopping service '{service_name}': {e}. Standard Error: {e.stderr}"

    def restart_service(self, service_name):
        """
        Restarts a service using systemctl.

        Args:
            service_name: The name of the service to restart.
        """
        try:
            subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
            return True, f"Service '{service_name}' restarted."
        except subprocess.CalledProcessError as e:
            return False, f"Error restarting service '{service_name}': {e}. Standard Error: {e.stderr}"
    

    def check_service_status(self, service_name):
        """
        Checks the status of a service using systemctl.

        Args:
            service_name: The name of the service to check.
        """
        try:
            subprocess.run(["sudo", "systemctl", "status", service_name], check=True)
            return True, f"Service '{service_name}' is active."
        except subprocess.CalledProcessError as e:
            return False, f"Error checking status of service '{service_name}': {e}. Standard Error: {e.stderr}"

    def delete_service(self, service_name):
        """
        Deletes a service using systemctl.

        Args:
            service_name: The name of the service to delete.
        """
        service_file_path = os.path.join(self.service_file_directory, f"{service_name}.service")
        try:
            self.stop_service(service_name)
            subprocess.run(["sudo", "systemctl", "disable", service_name], check=True)
            os.remove(service_file_path)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            return True, f"Service '{service_name}' deleted."
        except subprocess.CalledProcessError as e:
            return False, f"Error deleting service '{service_name}': {e}. Standard Error: {e.stderr}"