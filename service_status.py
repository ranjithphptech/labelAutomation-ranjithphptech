import subprocess

def check_service_status(service_name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout.strip() == "active":
            return f"Service '{service_name}' is running."
        else:
            return f"Service '{service_name}' is not running."
    except Exception as e:
        return f"Error checking service status: {e}"

# Example usage
service_name = "nginx"  # Change to the service you want to check
print(check_service_status(service_name))
