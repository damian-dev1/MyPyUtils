import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

class AppConfig:
    """Configuration constants and metadata for the Incident Form application."""
    WINDOW_TITLE = "E-Commerce Technical Incident Analysis Tool"
    WINDOW_GEOMETRY = "950x750"

    FIELD_OPTIONS = {
        "PLATFORMS": [
            "Magento2", "SAP", "Virtualstock", "HarveyNorman API",
            "SFTP / File Transfer", "Warehouse System", "Third-Party Logistics", "Website / Frontend"
        ],
        "INCIDENT_TYPES": [
            "OrderSyncFailure", "InventoryMismatch", "PriceDiscrepancy", "PromotionError",
            "APIResponseTimeout", "AuthenticationFailure", "DataValidationError", "MalformedPayload",
            "DuplicateOrder", "FileUploadFailure", "MissingSupplierDetails", "ScheduledJobFailure",
            "IntegrationFailure", "NetworkLatency", "SystemDowntime", "SecurityBreach"
        ],
        "STATUSES": ["Open", "In Progress", "Monitoring", "Resolved", "Closed", "Deferred"],
        "HTTP_METHODS": ["POST", "GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    }

    REQUIRED_FIELDS = ["incident_id", "reported_by", "platform", "incident_type", "summary", "details"]


# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------

class IncidentFormApp(tk.Tk):
    """Main GUI application for technical incident reporting, troubleshooting and analysis."""

    def __init__(self):
        super().__init__()
        self.title(AppConfig.WINDOW_TITLE)
        self.geometry(AppConfig.WINDOW_GEOMETRY)
        self.minsize(300, 400)

        self.widgets: dict[str, tk.Widget] = {}
        self.check_vars: dict[str, tk.BooleanVar] = {}

        self._create_ui()

    # --------------------------- UI Scaffold ---------------------------

    def _create_ui(self):
        """Builds the main Notebook (tabbed interface)."""
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Dedicated SFTP troubleshooting tab
        sftp_tab = ttk.Frame(notebook, padding=10)
        notebook.add(sftp_tab, text="SFTP Troubleshooting")
        self._populate_sftp_tab(sftp_tab)

        # Core incident tabs
        tabs = {
            "Core Details": self._populate_core_tab,
            "Classification": self._populate_classification_tab,
            "Technical Analysis": self._populate_technical_tab,
            "Impact & Metrics": self._populate_impact_tab,
            "API & Integration": self._populate_api_tab,
        }
        for label, func in tabs.items():
            frame = ttk.Frame(notebook, padding=10)
            notebook.add(frame, text=label)
            func(frame)

        # Bottom actions
        self._create_buttons()

        # Defaults
        self._set_initial_values()

    # --------------------------- SFTP Tab ------------------------------

    def _add_readonly_section(self, parent: ttk.Frame, title: str, content: str, row: int, height: int = 6):
        """Small helper: labeled, read-only text box with a Copy button."""
        # Title row
        title_row = ttk.Frame(parent)
        title_row.grid(column=0, row=row, sticky="w", padx=5, pady=(8, 2))
        ttk.Label(title_row, text=title, font=("Segoe UI", 10, "bold")).pack(side="left")
        btn = ttk.Button(title_row, text="Copy", command=lambda: self._copy_to_clipboard(content))
        btn.pack(side="left", padx=8)

        # Text row
        txt = tk.Text(parent, width=100, height=height, wrap="none",
                      relief="solid", borderwidth=1)
        txt.insert("1.0", content)
        txt.config(state="disabled")
        txt.grid(column=0, row=row + 1, sticky="ew", padx=5)
        parent.grid_columnconfigure(0, weight=1)

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # now it stays after the app exits (optional)
        messagebox.showinfo("Copied", "Content copied to clipboard.")

    def _populate_sftp_tab(self, tab: ttk.Frame):
        """Minimal, logically grouped SFTP reference with examples."""
        # Paths (top)
        self._add_readonly_section(tab, "Download Path", "live/incoming/products/", 0, height=2)
        self._add_readonly_section(tab, "Upload Path", "live/incoming/products/results", 2, height=2)

        # Inventory
        inv_files = "301471_INVENTORY_X114_20250911163307.csv.DONE\n301471_INVENTORY_X114_20250911163307.csv"
        inv_content = (
            "part_number,free_stock,supplier_free_stock,invent_status,low_inv_threshold,open_orders\n"
            "P-3596,24,24,IN_STOCK,,0"
        )
        self._add_readonly_section(tab, "Example Inventory Files", inv_files, 4, height=3)
        self._add_readonly_section(tab, "Inventory File Content", inv_content, 6, height=4)

        # Products
        prod_files = "301203_PRODUCT_X114_20250911145251.csv.DONE\n301203_PRODUCT_X114_20250911145251.csv"
        prod_content = (
            "part_number,bigbuys_sports_size,comp_stem_suitableforages,link_youtube,image,...,gcc_code,sap_article_ID,barcode,...\n"
            "4017449,,,,,,,,,,,,,,GARDENCARE DROPSHIP|PEST CONTROL|HOUSEHOLD PEST CONTROL|01125GDSPESWPC,12545242,8721158447340,..."
        )
        self._add_readonly_section(tab, "Example Product Files", prod_files, 8, height=3)
        self._add_readonly_section(tab, "Product File Content", prod_content, 10, height=4)

        # Pricing
        pr_files = "301393_PRICING_X114_20250911145332.csv.DONE\n301393_PRICING_X114_20250911145332.csv"
        pr_content = (
            "part_number,hn_buy_price,rrp,tax_class_id\n"
            "1539095330852,18.15,24.95,10% GST\n"
            "8538711851236,5.09,7,10% GST"
        )
        self._add_readonly_section(tab, "Example Pricing Files", pr_files, 12, height=3)
        self._add_readonly_section(tab, "Pricing File Content", pr_content, 14, height=4)

    # ----------------------------- Tabs --------------------------------

    def _populate_core_tab(self, parent: ttk.Frame):
        parent.columnconfigure(1, weight=1)
        self._create_field(parent, "incident_id", "entry", "Incident ID:", 0)
        self._create_field(parent, "timestamp", "entry", "Timestamp (UTC):", 1)
        self._create_field(parent, "reported_by", "entry", "Reported By:", 2)
        self._create_field(parent, "summary", "entry", "Summary:", 3, width=80)
        self._create_field(parent, "is_customer_facing", "check", "Customer-Facing Issue?", 4)

        ttk.Button(parent, text="↻ Refresh Timestamp", width=20,
                   command=self._refresh_timestamp).grid(column=2, row=1, padx=10)

    def _populate_classification_tab(self, parent: ttk.Frame):
        parent.columnconfigure(1, weight=1)
        self._create_field(parent, "platform", "dropdown", "Platform:", 0, AppConfig.FIELD_OPTIONS["PLATFORMS"])
        self._create_field(parent, "incident_type", "dropdown", "Incident Type:", 1, AppConfig.FIELD_OPTIONS["INCIDENT_TYPES"])
        self._create_field(parent, "status", "dropdown", "Status:", 2, AppConfig.FIELD_OPTIONS["STATUSES"])
        self._create_field(parent, "priority", "spinbox", "Priority (1=High):", 3, (1, 5))
        self._create_field(parent, "tags", "text", "Tags (comma-separated):", 4, height=3)

    def _populate_technical_tab(self, parent: ttk.Frame):
        parent.columnconfigure(1, weight=1)
        self._create_field(parent, "details", "text", "Observed Behavior / Error:", 0, height=8)
        self._create_field(parent, "root_cause", "text", "Root Cause:", 1, height=5)
        self._create_field(parent, "resolution", "text", "Resolution Steps:", 2, height=5)

    def _populate_impact_tab(self, parent: ttk.Frame):
        parent.columnconfigure(1, weight=1)
        self._create_field(parent, "affected_systems", "text", "Affected Systems:", 0, height=3)
        self._create_field(parent, "impacted_orders", "text", "Impacted Orders:", 1, height=5)
        self._create_field(parent, "response_time", "entry", "Response Time (minutes):", 2)
        self._create_field(parent, "resolved_time", "entry", "Resolved Time (UTC, Optional):", 3)
        self._create_field(parent, "requires_escalation", "check", "Requires Escalation?", 4)

    def _populate_api_tab(self, parent: ttk.Frame):
        parent.columnconfigure(1, weight=1)
        self._create_field(parent, "source_system", "dropdown", "Source System:", 0, AppConfig.FIELD_OPTIONS["PLATFORMS"])
        self._create_field(parent, "destination_system", "dropdown", "Destination System:", 1, AppConfig.FIELD_OPTIONS["PLATFORMS"])
        self._create_field(parent, "api_endpoint", "entry", "API Endpoint URL:", 2, width=100)

        details = ttk.Frame(parent)
        details.grid(column=0, row=3, columnspan=2, sticky="ew", pady=5)
        ttk.Label(details, text="HTTP Method:").pack(side="left", padx=5)
        method = ttk.Combobox(details, values=AppConfig.FIELD_OPTIONS["HTTP_METHODS"],
                              width=10, state="readonly")
        method.pack(side="left", padx=5)
        self.widgets["http_method"] = method

        ttk.Label(details, text="Status Code:").pack(side="left", padx=15)
        code = ttk.Entry(details, width=8)
        code.pack(side="left", padx=5)
        self.widgets["http_status_code"] = code

        ttk.Label(details, text="Correlation ID:").pack(side="left", padx=15)
        corr = ttk.Entry(details, width=40)
        corr.pack(side="left", fill="x", expand=True)
        self.widgets["correlation_id"] = corr

        frame = ttk.LabelFrame(parent, text="Payloads", padding=10)
        frame.grid(column=0, row=4, columnspan=2, sticky="nsew", pady=10)
        parent.grid_rowconfigure(4, weight=1)
        for c in range(2):
            frame.grid_columnconfigure(c, weight=1)

        ttk.Label(frame, text="Request Body").grid(row=0, column=0, sticky="w")
        req = tk.Text(frame, height=10, wrap="word", relief="solid", borderwidth=1)
        req.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        self.widgets["request_body"] = req

        ttk.Label(frame, text="Response Body / Error").grid(row=0, column=1, sticky="w")
        res = tk.Text(frame, height=10, wrap="word", relief="solid", borderwidth=1)
        res.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        self.widgets["response_body"] = res

    # ----------------------------- Widgets -----------------------------

    def _create_field(self, parent, key, wtype, label, row, *options, **kwargs):
        """Creates labeled form fields of various types."""
        ttk.Label(parent, text=label).grid(column=0, row=row, sticky="nw", padx=5, pady=6)
        width = kwargs.get("width", 70)
        widget = None

        if wtype == "entry":
            widget = ttk.Entry(parent, width=width)
        elif wtype == "dropdown":
            vals = options[0]
            widget = ttk.Combobox(parent, values=vals, width=max(10, width - 3), state="readonly")
        elif wtype == "text":
            widget = tk.Text(parent, width=width, height=kwargs.get("height", 4),
                             wrap="word", relief="solid", borderwidth=1)
        elif wtype == "check":
            var = tk.BooleanVar()
            widget = ttk.Checkbutton(parent, variable=var)
            self.check_vars[key] = var
        elif wtype == "spinbox":
            frm, to = options[0]
            widget = ttk.Spinbox(parent, from_=frm, to=to, width=10, state="readonly")

        if widget:
            widget.grid(column=1, row=row, sticky="ew", padx=5, pady=6)
            parent.grid_columnconfigure(1, weight=1)
            self.widgets[key] = widget

    # --------------------------- Buttons -------------------------------

    def _create_buttons(self):
        """Bottom control bar (Submit / Clear)."""
        frame = ttk.Frame(self)
        frame.pack(side="bottom", fill="x", padx=10, pady=10)
        frame.columnconfigure((0, 1), weight=1)

        ttk.Button(frame, text="Clear Form", command=self._clear_form).grid(
            row=0, column=0, sticky="e", padx=5
        )
        ttk.Button(frame, text="Submit Incident", command=self._submit).grid(
            row=0, column=1, sticky="w", padx=5
        )

    # --------------------------- State & Utils -------------------------

    def _set_initial_values(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if "timestamp" in self.widgets:
            self.widgets["timestamp"].delete(0, "end")
            self.widgets["timestamp"].insert(0, now)
        if "status" in self.widgets:
            self.widgets["status"].set("Open")
        if "priority" in self.widgets:
            self.widgets["priority"].set("3")
        if "incident_id" in self.widgets:
            self.widgets["incident_id"].focus()

    def _refresh_timestamp(self):
        """Refreshes the timestamp field."""
        if "timestamp" in self.widgets:
            self.widgets["timestamp"].delete(0, "end")
            self.widgets["timestamp"].insert(0, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    # --------------------------- Validation ----------------------------

    def _validate_inputs(self):
        """Checks required fields and types."""
        for key in AppConfig.REQUIRED_FIELDS:
            widget = self.widgets.get(key)
            if widget is None:
                messagebox.showerror("Validation Error", f"Missing widget for '{key}'.")
                return False
            value = widget.get("1.0", "end-1c").strip() if isinstance(widget, tk.Text) else widget.get().strip()
            if not value:
                widget.focus()
                messagebox.showerror("Validation Error", f"'{key.replace('_', ' ').title()}' is required.")
                return False

        resp_time_w = self.widgets.get("response_time")
        if resp_time_w:
            resp_time = resp_time_w.get()
            if resp_time and not resp_time.isdigit():
                messagebox.showerror("Validation Error", "Response Time must be a number.")
                resp_time_w.focus()
                return False

        code = self.widgets.get("http_status_code")
        if code and code.get() and not code.get().isdigit():
            messagebox.showerror("Validation Error", "HTTP Status Code must be numeric.")
            code.focus()
            return False

        return True

    # --------------------------- Data ---------------------------------

    def _collect_data(self):
        """Collects and formats all field values."""
        data = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                value = widget.get("1.0", "end-1c").strip()
                if key in ["tags", "affected_systems", "impacted_orders"]:
                    data[key] = [x.strip() for x in value.split(",") if x.strip()]
                else:
                    data[key] = value
            elif isinstance(widget, ttk.Checkbutton):
                # handled separately by self.check_vars
                continue
            else:
                data[key] = widget.get().strip()

        # Booleans
        for k, var in self.check_vars.items():
            data[k] = var.get()

        # Normalize response time
        rt = data.pop("response_time", "")
        data["response_time_minutes"] = int(rt) if rt else None
        return data

    # --------------------------- Submit / Clear ------------------------

    def _submit(self):
        """Handles incident form submission (preview only)."""
        if not self._validate_inputs():
            return
        try:
            data = self._collect_data()
            # Compact preview (no API call here by design)
            lines = ["Incident submitted successfully!"]
            for k, v in data.items():
                vv = ", ".join(v) if isinstance(v, list) else v
                if isinstance(vv, str) and len(vv) > 120:
                    vv = vv[:120] + "…"
                lines.append(f"• {k.replace('_', ' ').title()}: {vv}")
            messagebox.showinfo("Success", "\n".join(lines))
            self._clear_form()
        except Exception as e:
            messagebox.showerror("Submission Error", f"Unexpected error: {e}")

    def _clear_form(self):
        """Resets all fields."""
        for w in self.widgets.values():
            if isinstance(w, tk.Text):
                w.delete("1.0", "end")
            elif isinstance(w, (ttk.Entry, ttk.Combobox, ttk.Spinbox)):
                try:
                    w.set("")
                except Exception:
                    # Some Entry widgets don't have set(); fall back
                    w.delete(0, "end")
        for var in self.check_vars.values():
            var.set(False)
        self._set_initial_values()


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app = IncidentFormApp()
    app.mainloop()
