import frappe

def get_client_ip():
    request = frappe.local.request
    x_forwarded_for = request.environ.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.environ.get("REMOTE_ADDR", "")

def check_ip_on_login(login_manager):
    user_email = login_manager.user

    if user_email in ("Administrator", "Guest"):
        return

    allowed_ip = frappe.db.get_value("User", user_email, "allowed_ip")

    if not allowed_ip:
        return

    current_ip = get_client_ip()
    allowed_ips = [ip.strip() for ip in allowed_ip.split(",")]

    if current_ip not in allowed_ips:
        frappe.throw(
            msg=f"Access Denied! آپ کا IP ({current_ip}) allowed نہیں ہے۔",
            title="IP Block",
            exc=frappe.AuthenticationError
        )