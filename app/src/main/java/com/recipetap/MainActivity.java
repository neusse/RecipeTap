package com.recipetap;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.net.Uri;
import android.webkit.WebChromeClient;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import android.view.WindowManager;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileInputStream;
import java.io.ByteArrayInputStream;
import java.io.InputStream;

public class MainActivity extends Activity {
    private WebView web;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(0xff729b3f);
        getWindow().setNavigationBarColor(0xff729b3f);
        web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(true);
        web.addJavascriptInterface(new Object() {
            @JavascriptInterface public void setKeepAwake(boolean keep) {
                runOnUiThread(() -> {
                    if (keep) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                });
            }
        }, "AndroidBridge");
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) { receiveShare(getIntent()); }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!"recipetap.local".equals(uri.getHost())) return null;
                String name = uri.getLastPathSegment();
                if (name != null && name.matches("[0-9a-fA-F-]{36}\\.(png|jpg|gif|webp)") && uri.getPath().startsWith("/photos/")) {
                    File directory = getExternalFilesDir(null);
                    File photo = directory == null ? null : new File(new File(directory, "photos"), name);
                    if (photo != null && photo.isFile()) {
                        try {
                            String type = name.endsWith(".jpg") ? "image/jpeg" : name.endsWith(".gif") ? "image/gif" : name.endsWith(".webp") ? "image/webp" : "image/png";
                            return new WebResourceResponse(type, null, new FileInputStream(photo));
                        } catch (java.io.FileNotFoundException ignored) { }
                    }
                }
                WebResourceResponse missing = new WebResourceResponse("text/plain", "UTF-8", new ByteArrayInputStream(new byte[0]));
                missing.setStatusCodeAndReasonPhrase(404, "Not Found");
                return missing;
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (!request.isForMainFrame()) return false;
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                }
                return true;
            }
        });
        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    private void receiveShare(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        Uri stream = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        if (stream != null) {
            intent.setAction(null);
            new Thread(() -> saveSharedFile(stream)).start();
            return;
        }
        String value = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (value != null) web.evaluateJavascript("window.receiveShare(" + org.json.JSONObject.quote(value) + ")", null);
        intent.setAction(null);
    }

    private void saveSharedFile(Uri stream) {
        File destination = new File(getExternalFilesDir(null), "cheftap-snapshot.zip");
        try (InputStream input = getContentResolver().openInputStream(stream);
             FileOutputStream output = new FileOutputStream(destination)) {
            if (input == null) throw new java.io.IOException("Shared file could not be opened");
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            runOnUiThread(() -> Toast.makeText(this, "Saved ChefTap snapshot locally", Toast.LENGTH_LONG).show());
        } catch (Exception error) {
            destination.delete();
            runOnUiThread(() -> Toast.makeText(this, "Could not save shared file: " + error.getMessage(), Toast.LENGTH_LONG).show());
        }
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        receiveShare(intent);
    }

    @Override public void onBackPressed() {
        web.evaluateJavascript("window.goBack()", null);
    }
}
