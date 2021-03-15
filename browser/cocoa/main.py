from AppKit import (
    NSApplication,
)
from Foundation import NSBundle
from PyObjCTools import AppHelper

from browser.cocoa.app_delegate import AppDelegate


def main():
    # XXX: info.plist is generated by pyinstaller
    # bundle = NSBundle.mainBundle()
    # if bundle:
    #     app_info = bundle.infoDictionary()
    #     if app_info:
    #         app_info['CFBundleName'] = "App"
    #         app_info["NSAppTransportSecurity"] = {
    #             "NSAllowsArbitraryLoads": True,
    #             "NSAllowsArbitraryLoadsForMedia": True,
    #             "NSAllowsArbitraryLoadsInWebContent": True,
    #         }

    app = NSApplication.sharedApplication()
    # we must keep a reference to the delegate object ourselves,
    # NSApp.setDelegate_() doesn't retain it. A local variable is
    # enough here.
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    AppHelper.runEventLoop()
