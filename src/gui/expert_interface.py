import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time

# Minimal, dependency-free "expert" trading interface.
# Contract (simple):
# - Inputs: user actions (create order, submit for approval, approve/reject)
# - Outputs: prints/logs to the Logs tab; callbacks/hooks are left as extension points
# - Error modes: shows message boxes for invalid input; non-blocking UI using threads
#
# Integration notes: Import and call your project's ApprovalManager where available:
# from src.trading.approval import manager as approval_manager
# Use approval_manager.submit(request) / approval_manager.approve(id) etc.
from src.trading.approval import manager as approval_manager
from src.trading.execution import ExecutionGateway
from src.trading.strategy_runner import run_strategy

class ExpertTradingInterface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Expert Trading Automation Console')
        self.geometry('1000x700')

        self._create_widgets()
        self._start_clock()

    def _create_widgets(self):
        # Top frame with status
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X)

        self.clock_label = ttk.Label(top, text='--:--:--')
        self.clock_label.pack(side=tk.RIGHT, padx=8)

        title = ttk.Label(top, text='Expert Trading Automation', font=('Helvetica', 16, 'bold'))
        title.pack(side=tk.LEFT, padx=8, pady=8)

        # Main notebook
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Overview tab
        self.overview_frame = ttk.Frame(nb)
        nb.add(self.overview_frame, text='Overview')
        self._build_overview(self.overview_frame)

        # Order Ticket
        self.order_frame = ttk.Frame(nb)
        nb.add(self.order_frame, text='Order Ticket')
        self._build_order_ticket(self.order_frame)

        # Approvals
        self.approval_frame = ttk.Frame(nb)
        nb.add(self.approval_frame, text='Approvals')
        self._build_approvals(self.approval_frame)

        # Strategy Editor (minimal)
        self.strategy_frame = ttk.Frame(nb)
        nb.add(self.strategy_frame, text='Strategy')
        self._build_strategy(self.strategy_frame)

        # Logs
        self.log_frame = ttk.Frame(nb)
        nb.add(self.log_frame, text='Logs')
        self._build_logs(self.log_frame)

    def _build_overview(self, parent):
        # Placeholder: display account summary and key metrics
        lbl = ttk.Label(parent, text='Account Summary', font=('Helvetica', 12, 'bold'))
        lbl.pack(anchor=tk.W, padx=8, pady=(8,4))

        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=8)

        ttk.Label(frame, text='Cash:').grid(row=0, column=0, sticky=tk.W)
        self.cash_var = tk.StringVar(value='10,000,000 KRW')
        ttk.Label(frame, textvariable=self.cash_var).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame, text='Positions:').grid(row=1, column=0, sticky=tk.W, pady=(6,0))
        self.positions_box = scrolledtext.ScrolledText(parent, height=8, state='disabled')
        self.positions_box.pack(fill=tk.BOTH, expand=False, padx=8, pady=(4,8))
        self._append_positions('AAPL: 100 @ 150.00\nTSLA: 20 @ 230.00')

    def _build_order_ticket(self, parent):
        frm = ttk.Frame(parent)
        frm.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(frm, text='Symbol:').grid(row=0, column=0, sticky=tk.W)
        self.symbol_entry = ttk.Entry(frm, width=12)
        self.symbol_entry.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frm, text='Side:').grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.side_combo = ttk.Combobox(frm, values=['BUY', 'SELL'], width=8)
        self.side_combo.current(0)
        self.side_combo.grid(row=0, column=3, sticky=tk.W)

        ttk.Label(frm, text='Qty:').grid(row=1, column=0, sticky=tk.W, pady=(6,0))
        self.qty_entry = ttk.Entry(frm, width=12)
        self.qty_entry.grid(row=1, column=1, sticky=tk.W, pady=(6,0))

        ttk.Label(frm, text='Order Type:').grid(row=1, column=2, sticky=tk.W, padx=(10,0))
        self.type_combo = ttk.Combobox(frm, values=['MARKET', 'LIMIT'], width=10)
        self.type_combo.current(0)
        self.type_combo.grid(row=1, column=3, sticky=tk.W, pady=(6,0))

        ttk.Label(frm, text='Price (if LIMIT):').grid(row=2, column=0, sticky=tk.W, pady=(6,0))
        self.price_entry = ttk.Entry(frm, width=12)
        self.price_entry.grid(row=2, column=1, sticky=tk.W, pady=(6,0))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)

        submit_btn = ttk.Button(btn_frame, text='Submit Order', command=self._on_submit_order)
        submit_btn.pack(side=tk.LEFT)

        submit_approve_btn = ttk.Button(btn_frame, text='Submit for Approval', command=self._on_submit_for_approval)
        submit_approve_btn.pack(side=tk.LEFT, padx=8)

    # Execution mode selector
    mode_frm = ttk.Frame(parent)
    mode_frm.pack(fill=tk.X, padx=8)
    ttk.Label(mode_frm, text='Execution Mode:').pack(side=tk.LEFT)
    self.exec_mode = tk.StringVar(value='SIM')
    ttk.Radiobutton(mode_frm, text='SIM', variable=self.exec_mode, value='SIM', command=self._on_mode_change).pack(side=tk.LEFT, padx=4)
    ttk.Radiobutton(mode_frm, text='LIVE', variable=self.exec_mode, value='LIVE', command=self._on_mode_change).pack(side=tk.LEFT, padx=4)

    def _build_approvals(self, parent):
        lbl = ttk.Label(parent, text='Pending Approvals', font=('Helvetica', 12, 'bold'))
        lbl.pack(anchor=tk.W, padx=8, pady=(8,4))

        self.approval_list = ttk.Treeview(parent, columns=('id','symbol','side','qty','status'), show='headings')
        for c in ('id','symbol','side','qty','status'):
            self.approval_list.heading(c, text=c)
            self.approval_list.column(c, width=120)
        self.approval_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Example row
        self.approval_list.insert('', 'end', values=(1,'AAPL','BUY',100,'PENDING'))

        btns = ttk.Frame(parent)
        btns.pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(btns, text='Approve Selected', command=self._approve_selected).pack(side=tk.LEFT)
        ttk.Button(btns, text='Reject Selected', command=self._reject_selected).pack(side=tk.LEFT, padx=8)

    # refresh button
    ttk.Button(btns, text='Refresh', command=self._refresh_pending).pack(side=tk.RIGHT)

    def _build_strategy(self, parent):
        lbl = ttk.Label(parent, text='Strategy Editor (minimal)', font=('Helvetica', 12, 'bold'))
        lbl.pack(anchor=tk.W, padx=8, pady=(8,4))

        self.strategy_text = scrolledtext.ScrolledText(parent)
        self.strategy_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.strategy_text.insert('1.0', '# Define strategy logic here (python-like pseudo)\n')

        ttk.Button(parent, text='Save Strategy (not implemented)', command=lambda: messagebox.showinfo('Info','Save not implemented')).pack(pady=(0,8))
    ttk.Button(parent, text='Run Strategy', command=self._run_strategy).pack(pady=(0,8))

    def _build_logs(self, parent):
        self.log_text = scrolledtext.ScrolledText(parent, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _append_log(self, line):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {line}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def _append_positions(self, text):
        self.positions_box.configure(state='normal')
        self.positions_box.delete('1.0', tk.END)
        self.positions_box.insert(tk.END, text)
        self.positions_box.configure(state='disabled')

    def _on_submit_order(self):
        symbol = self.symbol_entry.get().strip()
        side = self.side_combo.get()
        qty = self.qty_entry.get().strip()
        otype = self.type_combo.get()
        price = self.price_entry.get().strip()

        if not symbol or not qty.isdigit():
            messagebox.showerror('Invalid', 'Symbol and integer Qty required')
            return

        order = dict(symbol=symbol, side=side, qty=int(qty), type=otype, price=price)
        self._append_log(f"Order submitted: {order}")

        res = self.execution.send_order(order)
        if res.get('status') == 'ok':
            self._append_log(f"Executed order (mode={self.execution.mode}): {res['report']}")
        else:
            self._append_log(f"Execution failed: {res.get('reason')}")

    def _on_submit_for_approval(self):
        # Create a request and (optionally) call ApprovalManager
        symbol = self.symbol_entry.get().strip()
        side = self.side_combo.get()
        qty = self.qty_entry.get().strip()
        if not symbol or not qty.isdigit():
            messagebox.showerror('Invalid', 'Symbol and integer Qty required')
            return
        req = dict(symbol=symbol, side=side, qty=int(qty), requested_by='expert')
        self._append_log(f"Submitted for approval: {req}")

    # Submit to ApprovalManager and refresh pending list
    aid = approval_manager.submit(req)
    self._append_log(f"Approval requested (id={aid})")
    self._refresh_pending()

    def _approve_selected(self):
        sel = self.approval_list.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select a pending approval')
            return
        for item in sel:
            vals = self.approval_list.item(item, 'values')
            approval_id = vals[0]
            approval_manager.approve(approval_id, operator='gui')
            self._append_log(f"Approved: {vals}")
            self.approval_list.set(item, 'status', 'APPROVED')

    def _reject_selected(self):
        sel = self.approval_list.selection()
        if not sel:
            messagebox.showinfo('Info', 'Select a pending approval')
            return
        for item in sel:
            vals = self.approval_list.item(item, 'values')
            approval_id = vals[0]
            approval_manager.reject(approval_id, operator='gui')
            self._append_log(f"Rejected: {vals}")
            self.approval_list.set(item, 'status', 'REJECTED')

    def _start_clock(self):
        def tick():
            while True:
                t = time.strftime('%H:%M:%S')
                try:
                    self.clock_label.config(text=t)
                except tk.TclError:
                    break
                time.sleep(1)
        t = threading.Thread(target=tick, daemon=True)
        t.start()

    # ---- new: integration plumbing ----
    def _on_mode_change(self):
        self.execution.set_mode(self.exec_mode.get())
        self._append_log(f"Execution mode set to {self.execution.mode}")

    def _refresh_pending(self):
        # populate the approval_list from approval_manager
        for it in self.approval_list.get_children():
            self.approval_list.delete(it)
        try:
            pending = approval_manager.list_pending()
            for rec in pending:
                aid = rec.get('approval_id')
                order = rec.get('order') or rec.get('signal') or {}
                self.approval_list.insert('', 'end', values=(aid, order.get('symbol',''), order.get('side',''), order.get('qty',''), rec.get('status','pending')))
        except Exception as e:
            self._append_log(f"Failed to refresh pending: {e}")

    def _on_approved_handler(self, rec):
        # Called by ApprovalManager when an approval is approved.
        try:
            order = rec.get('order') or rec.get('signal') or {}
            self._append_log(f"Approval handler triggered for {rec.get('approval_id')}, executing order: {order}")
            res = self.execution.send_order(order)
            if res.get('status') == 'ok':
                self._append_log(f"Auto-executed approved order: {res['report']}")
            else:
                self._append_log(f"Auto-execution failed: {res.get('reason')}")
        except Exception as e:
            self._append_log(f"Approval handler exception: {e}")

    def _run_strategy(self):
        code = self.strategy_text.get('1.0', 'end')
        self._append_log('Running strategy (sandbox) ...')
        # Provide a small ctx with read-only access to positions/cash
        ctx = {'cash': self.cash_var.get(), 'positions': self.positions_box.get('1.0', 'end')}
        try:
            out = run_strategy(code, ctx=ctx, timeout=5)
            if 'result' in out:
                self._append_log(f"Strategy result: {out['result']}")
            else:
                self._append_log(f"Strategy error: {out.get('error')}\n{out.get('trace','')}")
        except Exception as e:
            self._append_log(f"Strategy execution failed: {e}")

    # override mainloop start to register handlers and start periodic refresh
    def mainloop(self, *args, **kwargs):
        # initialize execution gateway
        self.execution = ExecutionGateway(mode=self.exec_mode.get())
        # register approval handler
        try:
            approval_manager.register_handler(self._on_approved_handler)
        except Exception:
            pass
        # initial pending populate
        self._refresh_pending()
        # schedule periodic refresh
        def periodic_refresh():
            try:
                while True:
                    time.sleep(5)
                    try:
                        self._refresh_pending()
                    except Exception:
                        pass
            except Exception:
                pass
        threading.Thread(target=periodic_refresh, daemon=True).start()
        super().mainloop(*args, **kwargs)


if __name__ == '__main__':
    app = ExpertTradingInterface()
    app._append_log('Expert Interface started')
    app.mainloop()
