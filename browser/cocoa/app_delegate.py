from logging import getLogger

from AppKit import (
    NSApplication,
    NSApp,
    NSBackingStoreBuffered,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusWindowLevel,
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
)

from server import AioHTTPServer
from cert import CertManager
from browser.cocoa.webview_controller import WebViewController
from browser.cocoa.keychain import Keychain

logger = getLogger(__name__)


class AppDelegate(NSObject):
    """ ApplicationDelegate
    """
    window = None

    #
    # NSApplicationDelegate protocols
    #
    def applicationDidFinishLaunching_(self, aNotification):
        logger.debug(f"applicationDidFinishLaunching: {aNotification}")

        certManager = CertManager()
        certManager.generate_certs()

        keychain = Keychain(b"my-example-app", b"PASSWORD")  # TODO: generate password
        clientCredential = keychain.importP12(certManager.client_p12,
                                              certManager.client_p12pass)

        self.server = AioHTTPServer()
        ctx = certManager.create_ssl_context()
        self.server.start(ctx=ctx)

        app = NSApplication.sharedApplication()
        app.setMainMenu_(self.createMainMenu())

        self.window = self.createWindow()

        # Get auto-saved frame
        frame = self.window.contentView().frame()
        webViewController = WebViewController.alloc().initWithFrame_(frame)
        webViewController.setServerCertificateFromPEM_(certManager.server_cert)
        webViewController.clientCredential = clientCredential
        webViewController.url = 'https://127.0.0.1:18760/'

        self.window.setContentViewController_(webViewController)
        self.window.setDelegate_(self)
        self.window.display()
        self.window.orderFrontRegardless()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, sender, flag):
        logger.debug(f"applicationShouldHandleReopen:hasVisibleWindows: {sender}, {flag}")
        return False

    def applicationShouldTerminate_(self, application):
        logger.debug(f"applicationShouldTerminate: {application}")
        return True

    def applicationWillTerminate_(self, aNotification):
        logger.debug(f"applicationWillTerminate: {aNotification}")
        self.server.stop()

    #
    # NSWindowDelegate
    #
    def windowWillClose_(self, aNotification):
        NSApp().terminate_(self)

    #
    # Owned methods
    #
    def createWindow(self) -> NSWindow:
        style = (NSWindowStyleMaskTitled |
                 NSWindowStyleMaskClosable |
                 NSWindowStyleMaskMiniaturizable |
                 NSWindowStyleMaskResizable)

        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(10, 10, 800, 600),  # Initial
            style,
            NSBackingStoreBuffered,
            False
        )
        window.setTitle_("My App")
        window.setLevel_(NSStatusWindowLevel)
        window.setFrameAutosaveName_("main-window")

        return window

    def createMainMenu(self):
        mainMenu = NSMenu.alloc().init()  # menu bar
        mainMenuItem = NSMenuItem.alloc().init()
        mainMenu.addItem_(mainMenuItem)

        # NOTE: The title of the first menu will automatically refer to CFBundleName.
        appMenu = NSMenu.alloc().init()

        appMenu.addItemWithTitle_action_keyEquivalent_(
            "About",
            "orderFrontStandardAboutPanel:",
            "",
        )
        appMenu.addItem_(NSMenuItem.separatorItem())
        appMenu.addItemWithTitle_action_keyEquivalent_(
            "Quit",
            "terminate:",
            "q",
        )

        mainMenuItem.setSubmenu_(appMenu)

        return mainMenu
