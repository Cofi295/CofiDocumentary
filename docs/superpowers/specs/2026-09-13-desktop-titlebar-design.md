# Desktop title bar design

Only the PyWebView desktop window gets a dark custom title bar. The browser view stays unchanged. The bar contains a COFI DOCUMENTARY label and minimize, maximize/restore, and close buttons. Its non-button area drags the native window. Window actions use a PyWebView JavaScript bridge; closing the window must not stop an already-running external backend. Verify layout, button behavior, and backend reuse without stopping the Footage worker.
