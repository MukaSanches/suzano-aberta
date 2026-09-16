import SwiftUI
import UIKit
import WebKit

struct WebAppView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = [.audio, .video]
        configuration.applicationNameForUserAgent = "SuzanoAbertaIOS/1.0.0"

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 244 / 255, green: 247 / 255, blue: 249 / 255, alpha: 1)
        webView.scrollView.backgroundColor = webView.backgroundColor
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.keyboardDismissMode = .interactive

        let refreshControl = UIRefreshControl()
        refreshControl.addTarget(context.coordinator, action: #selector(Coordinator.refresh(_:)), for: .valueChanged)
        webView.scrollView.refreshControl = refreshControl

        context.coordinator.attach(webView)
        context.coordinator.loadRemote()
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        private static let remoteURL = URL(string: "https://mukasanches.github.io/suzano-aberta/app/")!
        private static let trustedHost = "mukasanches.github.io"

        private weak var webView: WKWebView?
        private var usingFallback = false

        func attach(_ webView: WKWebView) {
            self.webView = webView
        }

        func loadRemote() {
            guard let webView else { return }
            usingFallback = false
            let request = URLRequest(
                url: Self.remoteURL,
                cachePolicy: .reloadRevalidatingCacheData,
                timeoutInterval: 20
            )
            webView.load(request)
        }

        @objc func refresh(_ sender: UIRefreshControl) {
            guard let webView else {
                sender.endRefreshing()
                return
            }
            if usingFallback {
                loadRemote()
            } else {
                webView.reload()
            }
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.cancel)
                return
            }

            if url.isFileURL || url.scheme == "about" {
                decisionHandler(.allow)
                return
            }

            let scheme = url.scheme?.lowercased()
            let host = url.host?.lowercased()
            if scheme == "https", host == Self.trustedHost {
                if navigationAction.targetFrame == nil {
                    webView.load(navigationAction.request)
                    decisionHandler(.cancel)
                } else {
                    decisionHandler(.allow)
                }
                return
            }

            if let scheme, ["http", "https", "mailto", "tel"].contains(scheme) {
                UIApplication.shared.open(url, options: [:], completionHandler: nil)
            }
            decisionHandler(.cancel)
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            webView.scrollView.refreshControl?.endRefreshing()
            if webView.url?.host?.lowercased() == Self.trustedHost {
                usingFallback = false
            }
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            handleMainFrameFailure(in: webView)
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            handleMainFrameFailure(in: webView)
        }

        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            if usingFallback {
                loadFallback(in: webView)
            } else {
                webView.reload()
            }
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            if let url = navigationAction.request.url,
               url.scheme == "https",
               url.host?.lowercased() == Self.trustedHost {
                webView.load(navigationAction.request)
            } else if let url = navigationAction.request.url {
                UIApplication.shared.open(url, options: [:], completionHandler: nil)
            }
            return nil
        }

        private func handleMainFrameFailure(in webView: WKWebView) {
            webView.scrollView.refreshControl?.endRefreshing()
            guard !usingFallback else { return }
            loadFallback(in: webView)
        }

        private func loadFallback(in webView: WKWebView) {
            let indexURL = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "www")
                ?? Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "app")
                ?? Bundle.main.url(forResource: "index", withExtension: "html")

            guard let indexURL else { return }
            usingFallback = true
            let directory = indexURL.deletingLastPathComponent()
            webView.loadFileURL(indexURL, allowingReadAccessTo: directory)
        }
    }
}
