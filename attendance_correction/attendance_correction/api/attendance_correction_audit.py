import frappe
import re
from frappe.utils import formatdate, format_datetime, flt


ALLOWED_FIELDS = {"duty hours", "attendance status", "overtime"}


def parse_correction_comment(comment_text):
    changes = []
    pattern = re.compile(
        r"([A-Za-z\s]+) changed from <b>(.*?)</b>\s*[→\->&]+\s*<b>(.*?)</b>",
        re.IGNORECASE,
    )
    numeric_fields = {"duty hours", "overtime"}

    for match in pattern.finditer(comment_text):
        field    = match.group(1).strip()
        from_val = match.group(2).strip()
        to_val   = match.group(3).strip()

        is_reduction = False
        if field.lower() in numeric_fields:
            try:
                is_reduction = flt(to_val) < flt(from_val)
            except Exception:
                pass

        changes.append({
            "field":        field,
            "from_value":   from_val,
            "to_value":     to_val,
            "is_reduction": is_reduction,
        })

    return changes


def get_user_info(user_id):
    """
    Returns dict with first_name and username for a given user_id.
    user_id can be email (name), username, or full_name.
    Falls back gracefully at each step.
    """
    if not user_id:
        return {"first_name": "", "username": ""}

    # Strategy 1: user_id is the User.name (email / 'Administrator')
    result = frappe.db.get_value(
        "User", user_id, ["first_name", "username"], as_dict=True
    )
    if result:
        return result

    # Strategy 2: user_id matches User.username
    result = frappe.db.get_value(
        "User", {"username": user_id}, ["first_name", "username"], as_dict=True
    )
    if result:
        return result

    # Strategy 3: user_id matches User.full_name
    result = frappe.db.get_value(
        "User", {"full_name": user_id}, ["first_name", "username"], as_dict=True
    )
    if result:
        return result

    # Fallback: return raw value so something is shown
    return {"first_name": user_id, "username": user_id}


@frappe.whitelist()
def get_correction_audit(
    from_date=None,
    to_date=None,
    employee=None,
    department=None,
    override_type="all",
):
    att_filters = {"docstatus": ["!=", 2]}
    if employee:
        att_filters["employee"] = employee
    if department:
        att_filters["department"] = department
    if from_date and to_date:
        att_filters["attendance_date"] = ["between", [from_date, to_date]]

    attendance_list = frappe.get_all(
        "Attendance",
        filters=att_filters,
        fields=["name", "employee", "employee_name", "department", "attendance_date"],
    )

    if not attendance_list:
        return []

    attendance_map = {a["name"]: a for a in attendance_list}
    att_names      = list(attendance_map.keys())

    comments = frappe.db.sql(
        """
        SELECT
            c.reference_name  AS attendance_name,
            COALESCE(NULLIF(c.comment_by, ''), c.owner)  AS comment_by,
            c.owner           AS owner,
            c.creation        AS changed_on,
            c.content         AS comment_text
        FROM `tabComment` c
        WHERE c.reference_doctype = 'Attendance'
          AND c.comment_type      = 'Info'
          AND c.reference_name    IN %(names)s
        ORDER BY c.creation DESC
        """,
        {"names": att_names},
        as_dict=True,
    )

    # Cache so we don't hit DB for every row
    user_info_cache = {}

    audit_rows = []

    for comment in comments:
        att = attendance_map.get(comment["attendance_name"])
        if not att:
            continue

        comment_by = comment["comment_by"] or ""

        # Fetch user info with cache
        if comment_by not in user_info_cache:
            user_info_cache[comment_by] = get_user_info(comment_by)
        uinfo = user_info_cache[comment_by]

        for change in parse_correction_comment(comment["comment_text"]):

            # ── Only show duty hours, attendance status, overtime ──
            if change["field"].lower() not in ALLOWED_FIELDS:
                continue

            if override_type == "reduction" and not change["is_reduction"]:
                continue
            if override_type == "increase" and change["is_reduction"]:
                continue

            label = (
                "Manual Reduction" if change["is_reduction"]
                else "Manual Increase" if change["field"].lower() in {"duty hours", "overtime"}
                else "Manual Edit"
            )

            audit_rows.append({
                "attendance_name": comment["attendance_name"],
                "employee":        att["employee"],
                "employee_name":   att["employee_name"],
                "department":      att.get("department", ""),
                "attendance_date": formatdate(att["attendance_date"], "dd-MM-yyyy")
                                   if att.get("attendance_date") else "",
                "changed_by":      comment_by,
                "first_name":      uinfo.get("first_name") or comment_by,
                "username":        uinfo.get("username") or comment_by,
                "changed_on":      format_datetime(comment["changed_on"], "dd-MM-yyyy HH:mm")
                                   if comment.get("changed_on") else "",
                "field_name":      change["field"],
                "from_value":      change["from_value"],
                "to_value":        change["to_value"],
                "is_reduction":    change["is_reduction"],
                "override_type":   label,
            })

    return audit_rows


@frappe.whitelist()
def get_audit_summary(from_date=None, to_date=None, department=None):
    rows = get_correction_audit(
        from_date=from_date,
        to_date=to_date,
        department=department,
    )

    if not rows:
        return {
            "total_corrections":  0,
            "total_reductions":   0,
            "employees_affected": 0,
            "most_reduced_field": "—",
        }

    field_counts = {}
    for r in rows:
        if r["is_reduction"]:
            field_counts[r["field_name"]] = field_counts.get(r["field_name"], 0) + 1

    return {
        "total_corrections":  len(rows),
        "total_reductions":   sum(1 for r in rows if r["is_reduction"]),
        "employees_affected": len({r["employee"] for r in rows}),
        "most_reduced_field": max(field_counts, key=field_counts.get) if field_counts else "—",
    }