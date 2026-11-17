const express = require('express');
const cors = require('cors');
const app = express();
app.use(cors({ origin: '*', credentials: true }));
app.get('/x', (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.json({ ok: true });
});
