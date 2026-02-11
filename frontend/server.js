const express = require("express");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 3000;
const PY_BACKEND = process.env.PY_BACKEND || "http://localhost:8000";

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

app.get("/connect-amazon", (req, res) => {
  const redirectUrl = `${PY_BACKEND}/auth/login`;
  res.redirect(redirectUrl);
});

app.post("/chat", async (req, res) => {
  try {
    const { message, profileId } = req.body;
    const resp = await fetch(`${PY_BACKEND}/agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, profile_id: profileId }),
    });
    const data = await resp.json();
    res.json(data);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to call backend" });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend running on http://localhost:${PORT}`);
});
