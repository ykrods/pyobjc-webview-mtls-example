import objc

from logging import getLogger
from typing import Callable

from AppKit import (
    NSApp,
    NSViewController,
)
from Foundation import (
    NSData,
    NSURL,
    NSURLAuthenticationChallenge,
    NSURLAuthenticationMethodServerTrust,
    NSURLAuthenticationMethodClientCertificate,
    NSURLCredential,
    NSURLProtectionSpace,
    NSURLRequest,
    NSURLRequestReloadIgnoringLocalCacheData,
    # NSURLSessionAuthChallengePerformDefaultHandling,
    NSURLSessionAuthChallengeUseCredential,
    NSURLSessionAuthChallengeCancelAuthenticationChallenge,
)
from Security import (
    SecCertificateCreateWithData,
    SecTrustSetAnchorCertificates,
    SecTrustEvaluateWithError,
)
from WebKit import (
    WKWebView,
    WKWebViewConfiguration,
)

logger = getLogger(__name__)


class WebViewController(NSViewController):
    url = None
    clientCredential = None

    def initWithFrame_(self, frame):
        self = objc.super(
            WebViewController,
            self
        ).initWithNibName_bundle_(None, None)

        if self is None:
            return None

        self.frame = frame

        return self

    def setServerCertificateFromPEM_(self, pem):
        cert_b64 = "".join(pem.decode().split("\n")[1:-2])
        data = NSData.alloc().initWithBase64EncodedString_options_(cert_b64, 0)
        self.serverCert = SecCertificateCreateWithData(None, data)

    def loadView(self):
        configuration = WKWebViewConfiguration.alloc().init()
        # Enable comunication between js and webview
        configuration.userContentController().addScriptMessageHandler_name_(self, "logging")

        self.webView = WKWebView.alloc().initWithFrame_configuration_(self.frame, configuration)
        self.webView.setNavigationDelegate_(self)
        self.setView_(self.webView)

    def viewDidLoad(self):
        super().viewDidLoad()

        request = NSURLRequest.requestWithURL_cachePolicy_timeoutInterval_(
            NSURL.URLWithString_(self.url),
            NSURLRequestReloadIgnoringLocalCacheData,
            3,
        )
        self.webView.loadRequest_(request)

    #
    # WKNavigationDelegate
    #
    def webView_didReceiveAuthenticationChallenge_completionHandler_(
            self,
            webView: WKWebView,
            challenge: NSURLAuthenticationChallenge,
            completionHandler: Callable,
    ):
        space: NSURLProtectionSpace = challenge.protectionSpace()

        if space.host() != "127.0.0.1":
            # completionHandler(NSURLSessionAuthChallengePerformDefaultHandling, None)
            completionHandler(NSURLSessionAuthChallengeCancelAuthenticationChallenge, None)
            return
        if space.authenticationMethod() == NSURLAuthenticationMethodServerTrust:
            self.performServerAuthWithTrust_handler_(space.serverTrust(), completionHandler)
            return

        if space.authenticationMethod() == NSURLAuthenticationMethodClientCertificate:
            self.performClientAuthWithHandler_(completionHandler)
            return

        completionHandler(NSURLSessionAuthChallengeCancelAuthenticationChallenge, None)

    def performServerAuthWithTrust_handler_(self, trust, completionHandler):
        SecTrustSetAnchorCertificates(trust, [self.serverCert])

        valid, error = SecTrustEvaluateWithError(trust, None)
        if not valid:
            logger.error(error)
            completionHandler(
                NSURLSessionAuthChallengeCancelAuthenticationChallenge,
                None
            )
            return

        credential = NSURLCredential.credentialForTrust_(trust)
        completionHandler(NSURLSessionAuthChallengeUseCredential, credential)

    def performClientAuthWithHandler_(self, completionHandler):
        if self.clientCredential:
            completionHandler(
                NSURLSessionAuthChallengeUseCredential,
                self.clientCredential
            )
        else:
            completionHandler(
                NSURLSessionAuthChallengeCancelAuthenticationChallenge,
                None
            )

    def webView_didFailNavigation_withError_(self, webview, navigation, error):
        logger.debug("webView:didFailNavigation:withError:")
        logger.debug(f"Error: {error}")

    def webView_didFailProvisionalNavigation_withError_(self, webview, navigation, error):
        logger.debug("webView:didFailProvisionalNavigation:withError:")
        logger.debug(f"Error: {error}")

    def webViewWebContentProcessDidTerminate_(self, error):
        logger.debug("webViewWebContentProcessDidTerminate")
        logger.debug(f"Error: {error}")

    # WKScriptMessageHandler protocol
    def userContentController_didReceiveScriptMessage_(self, userContentController, message):
        logger.debug(f"message {message.body()}")
