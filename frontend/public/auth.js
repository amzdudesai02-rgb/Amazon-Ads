// Simple front-end login gating for AMZ DUDES tool.
// Stores a boolean flag in localStorage and redirects unauthenticated users
// to login.html when they try to access protected pages.

(function () {
  const KEY = "amzads_logged_in";

  function isLoggedIn() {
    try {
      return window.localStorage.getItem(KEY) === "true";
    } catch (e) {
      return false;
    }
  }

  function login() {
    try {
      window.localStorage.setItem(KEY, "true");
    } catch (e) {
      // ignore
    }
  }

  function logout() {
    try {
      window.localStorage.removeItem(KEY);
    } catch (e) {
      // ignore
    }
  }

  function ensureAccess() {
    const path = window.location.pathname || "/";
    const isHome = path === "/" || path.endsWith("/index.html");
    const isLogin = path.endsWith("/login.html");
    const isSignup = path.endsWith("/signup.html");

    if (!isHome && !isLogin && !isSignup && !isLoggedIn()) {
      const redirectTarget = path + window.location.search;
      const qp = encodeURIComponent(redirectTarget);
      window.location.href = "/login.html?redirect=" + qp;
    }
  }

  // Expose helpers for the login page and potential future use.
  window.AmzAdsAuth = {
    isLoggedIn,
    login,
    logout,
  };

  // Enforce login on protected pages.
  ensureAccess();
})();

