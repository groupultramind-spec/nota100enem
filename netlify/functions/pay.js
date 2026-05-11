const https = require('https');
const QRCode = require('qrcode');

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };

  try {
    const body = event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString() : event.body;
    const { action, payload, credentials } = JSON.parse(body);

    // 1. AUTENTICAÇÃO
    const authData = await new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.syncpayments.com.br',
        path: '/api/partner/v1/auth-token',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }, res => {
        let d = '';
        res.on('data', chunk => d += chunk);
        res.on('end', () => resolve(JSON.parse(d)));
      });
      req.on('error', reject);
      req.write(JSON.stringify({
        client_id: credentials.key,
        client_secret: credentials.token,
        grant_type: 'client_credentials'
      }));
      req.end();
    });

    const token = authData.access_token || (authData.data && authData.data.access_token);
    if (!token) return { statusCode: 401, body: JSON.stringify({ error: 'Auth Failed', detail: authData }) };

    // 2. AÇÃO (CREATE_PIX ou CHECK_STATUS)
    const path = action === 'create_pix' 
      ? '/api/partner/v1/cash-in' 
      : `/api/partner/v1/transaction/${payload.transactionId}`;
    
    const method = action === 'create_pix' ? 'POST' : 'GET';

    const result = await new Promise((resolve, reject) => {
      const req = https.request({
        hostname: 'api.syncpayments.com.br',
        path: path,
        method: method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      }, res => {
        let d = '';
        res.on('data', chunk => d += chunk);
        res.on('end', () => resolve(JSON.parse(d)));
      });
      req.on('error', reject);
      if (method === 'POST') req.write(JSON.stringify(payload));
      req.end();
    });

    // Se for criação de PIX, gera o QR Code no backend
    if (action === 'create_pix' && (result.pix_code || (result.data && result.data.pix_code))) {
      const code = result.pix_code || result.data.pix_code;
      result.qr_code_base64 = await QRCode.toDataURL(code);
    }

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(result)
    };

  } catch (err) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: err.message })
    };
  }
};
