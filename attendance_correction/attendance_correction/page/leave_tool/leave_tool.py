import frappe
from frappe.utils import getdate


@frappe.whitelist()
def get_absent_records(employee, from_date, to_date):
    records = frappe.db.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "status": "Absent",
            "docstatus": 1,
        },
        fields=["name", "attendance_date", "status", "employee_name"],
        order_by="attendance_date asc",
    )
    return records


@frappe.whitelist()
def apply_leave(employee, leave_type, dates):
    import json

    if isinstance(dates, str):
        dates = json.loads(dates)

    results = []

    # ── Employee Info ─────────────────────────────────────────────────────────
    emp = frappe.db.get_value(
        "Employee",
        employee,
        ["company", "employee_name", "department"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("Employee not found.")

    for date in dates:
        try:
            # ── STEP 1: Cancel existing Absent Attendance ─────────────────────
            att_name = frappe.db.get_value(
                "Attendance",
                {
                    "employee": employee,
                    "attendance_date": date,
                    "docstatus": 1,
                },
                "name",
            )

            if att_name:
                att = frappe.get_doc("Attendance", att_name)
                att.flags.ignore_permissions = True
                att.cancel()
                frappe.db.commit()

            # ── STEP 2: Create new Attendance with On Leave ───────────────────
            existing_on_leave = frappe.db.exists(
                "Attendance",
                {
                    "employee": employee,
                    "attendance_date": date,
                    "status": "On Leave",
                    "docstatus": 1,
                },
            )

            if not existing_on_leave:
                new_att = frappe.new_doc("Attendance")
                new_att.employee = employee
                new_att.employee_name = emp.employee_name
                new_att.attendance_date = date
                new_att.status = "On Leave"
                new_att.company = emp.company
                new_att.flags.ignore_validate = True
                new_att.flags.ignore_mandatory = True
                new_att.flags.ignore_permissions = True
                new_att.insert(ignore_permissions=True)
                new_att.submit()
                frappe.db.commit()

            # ── STEP 3: Check duplicate Leave Application ─────────────────────
            existing_la = frappe.db.exists(
                "Leave Application",
                {
                    "employee": employee,
                    "from_date": date,
                    "to_date": date,
                    "docstatus": ["!=", 2],
                },
            )

            if existing_la:
                results.append({
                    "date": date,
                    "status": "skipped",
                    "reason": "Leave Application already exists: " + existing_la,
                })
                continue

            # ── STEP 4: Create Leave Application properly ─────────────────────
            # Must use proper submit() so on_submit fires
            # and Leave Ledger Entry is created (balance deduction)
            la = frappe.new_doc("Leave Application")
            la.employee = employee
            la.employee_name = emp.employee_name
            la.leave_type = leave_type
            la.from_date = date
            la.to_date = date
            la.total_leave_days = 1
            la.company = emp.company
            la.status = "Approved"
            la.half_day = 0
            la.posting_date = getdate()
            la.description = "Auto generated via Leave Tool"

            # Skip validate only — on_submit must fire for ledger entry
            la.flags.ignore_validate = True
            la.flags.ignore_mandatory = True
            la.flags.ignore_permissions = True
            la.flags.ignore_links = True

            la.insert(ignore_permissions=True)
            frappe.db.commit()

            # Submit properly so Leave Ledger Entry is created
            la.flags.ignore_validate = True
            la.flags.ignore_permissions = True
            la.flags.ignore_validate_update_after_submit = True
            la.submit()
            frappe.db.commit()

            results.append({
                "date": date,
                "status": "success",
                "reason": la.name,
            })

        except Exception as e:
            frappe.db.rollback()
            results.append({
                "date": date,
                "status": "error",
                "reason": str(e),
            })

    return results