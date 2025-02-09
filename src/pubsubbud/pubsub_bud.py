ws = make_ws()
cb = make_cb()
ws_interface = create_interface(ws.callback)
cb_interface = create_interface(cb.callback)
ps = make_ps()
ps.add_interface(ws_interface)
ps.add_interface(cb_interface)
ps.run()
