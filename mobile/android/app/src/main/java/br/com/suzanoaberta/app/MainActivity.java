package br.com.suzanoaberta.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

public final class MainActivity extends Activity {
    private static final String REMOTE_APP = "https://mukasanches.github.io/suzano-aberta/app/";
    private static final String LOCAL_APP = "file:///android_asset/www/index.html";

    private WebView webView;
    private boolean usingFallback = false;
    private OnBackInvokedCallback predictiveBackCallback;

    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(8, 31, 51));
        getWindow().setNavigationBarColor(Color.rgb(255, 255, 255));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(244, 247, 249));
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowContentAccess(false);
        settings.setAllowFileAccess(true);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setSupportMultipleWindows(false);
        settings.setUserAgentString(settings.getUserAgentString() + " SuzanoAbertaAndroid/1.0.0");

        CookieManager.getInstance().setAcceptCookie(false);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);
        WebView.setWebContentsDebuggingEnabled(false);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String host = uri.getHost();
                if (host == null) return false;
                if ("mukasanches.github.io".equalsIgnoreCase(host)) return false;

                Intent external = new Intent(Intent.ACTION_VIEW, uri);
                try {
                    startActivity(external);
                } catch (Exception ignored) {
                    // Sem aplicativo capaz de abrir a URL: a WebView permanece no estado atual.
                }
                return true;
            }

            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame() && !usingFallback) {
                    usingFallback = true;
                    view.loadUrl(LOCAL_APP);
                }
            }
        });

        registerBackNavigation();

        if (savedInstanceState == null) {
            webView.loadUrl(REMOTE_APP);
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    private void registerBackNavigation() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            predictiveBackCallback = this::handleBackNavigation;
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    predictiveBackCallback
            );
        }
    }

    private void handleBackNavigation() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            finishAfterTransition();
        }
    }

    @Override protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @SuppressLint("GestureBackNavigation")
    @Override public void onBackPressed() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            handleBackNavigation();
            return;
        }
        super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && predictiveBackCallback != null) {
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(predictiveBackCallback);
            predictiveBackCallback = null;
        }

        if (webView != null) {
            webView.stopLoading();
            webView.setWebChromeClient(null);
            webView.setWebViewClient(null);
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
