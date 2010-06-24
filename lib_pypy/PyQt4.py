from _rpyc_support import proxy_sub_module, remote_eval


for name in ("QtCore", "QtGui", "QtWebKit"):
    proxy_sub_module(globals(), name)

s = "__import__('PyQt4').QtGui.QDialogButtonBox."
QtGui.QDialogButtonBox.Cancel = remote_eval("%sCancel | %sCancel" % (s, s))
QtGui.QDialogButtonBox.Ok = remote_eval("%sOk | %sOk" % (s, s))
