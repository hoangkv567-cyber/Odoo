import secrets
import hashlib
import hmac
import time
from datetime import datetime

import pytz
from odoo import fields, http
from odoo.http import request


class ServiceWebsite(http.Controller):
    def _signed_token(self, payload):
        secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        session = hashlib.sha256(request.session.sid.encode()).hexdigest()
        return hmac.new(secret.encode(), (payload + '.' + session).encode(), hashlib.sha256).hexdigest()

    @http.route('/maintenance', type='http', auth='public', website=True, sitemap=True)
    def booking_form(self, **kwargs):
        payload = secrets.token_urlsafe(24) + '.' + str(int(time.time()))
        token = payload + '.' + self._signed_token(payload)
        products = request.env['product.product'].sudo().search([
            ('xyz_booking_service', '=', True), ('sale_ok', '=', True),
            ('website_published', '=', True), ('type', '=', 'service'),
        ])
        return request.render('xyz_service_core.booking_page', {'products': products, 'token': token, 'error': kwargs.get('error')})

    @http.route('/maintenance/book', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def book(self, **post):
        token = post.get('token', '')
        try:
            nonce, issued, signature = token.split('.')
            valid = bool(nonce) and 0 <= time.time() - int(issued) <= 86400 and hmac.compare_digest(signature, self._signed_token(nonce + '.' + issued))
        except (ValueError, TypeError):
            valid = False
        if not valid:
            return request.make_response('Invalid booking session', status=400)
        # Serialize retries of the same session without trusting a client-supplied record ID.
        request.env.cr.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', [token])
        booking_model = request.env['xyz.booking'].sudo()
        if booking_model.search_count([('token', '=', token)]):
            return request.redirect('/maintenance/thanks')
        name, email = post.get('name', '').strip(), post.get('email', '').strip()
        address = post.get('address', '').strip()
        if not name or '@' not in email or not address or not post.get('equipment', '').strip():
            return request.redirect('/maintenance?error=missing')
        if any(len(post.get(key, '')) > 2000 for key in ('name', 'email', 'address', 'equipment', 'description', 'phone')):
            return request.make_response('Input too long', status=400)
        try:
            product_id = int(post.get('product_id', 0))
            desired = datetime.fromisoformat(post.get('requested_start', ''))
            if desired.tzinfo:
                raise ValueError('Use local time')
            desired = pytz.timezone('Asia/Ho_Chi_Minh').localize(desired).astimezone(pytz.UTC).replace(tzinfo=None)
            if desired < fields.Datetime.now():
                raise ValueError('Past date')
        except (ValueError, TypeError):
            return request.redirect('/maintenance?error=date')
        product = request.env['product.product'].sudo().search([
            ('id', '=', product_id), ('xyz_booking_service', '=', True),
            ('website_published', '=', True), ('sale_ok', '=', True), ('type', '=', 'service'),
        ], limit=1)
        if not product:
            return request.make_response('Unknown service', status=400)
        salesperson_id = request.env['ir.config_parameter'].sudo().get_param('xyz.salesperson_id')
        salesperson = request.env['res.users'].sudo().browse(int(salesperson_id)).exists() if salesperson_id else request.env.ref('base.user_admin')
        # Anonymous email is never used to claim an existing customer's identity or B2B prices.
        if request.env.user._is_public():
            partner = request.env['res.partner'].sudo().create({'name': name, 'email': email, 'phone': post.get('phone'), 'street': address, 'customer_rank': 1, 'user_id': salesperson.id})
            retail_id = request.env['ir.config_parameter'].sudo().get_param('xyz.retail_pricelist_id')
            if retail_id:
                partner.property_product_pricelist = int(retail_id)
        else:
            partner = request.env.user.partner_id
        equipment = request.env['xyz.equipment'].sudo().create({
            'name': post['equipment'].strip(), 'partner_id': partner.id, 'address': address,
            'user_id': salesperson.id,
        })
        booking_model.create({
            'token': token, 'partner_id': partner.id, 'equipment_id': equipment.id,
            'product_id': product.id, 'requested_start': desired,
            'description': post.get('description', ''), 'user_id': salesperson.id,
        })
        return request.redirect('/maintenance/thanks')

    @http.route('/maintenance/thanks', type='http', auth='public', website=True)
    def thanks(self, **kwargs):
        return request.render('xyz_service_core.booking_thanks')

    @http.route('/my/maintenance', type='http', auth='user', website=True)
    def my_jobs(self, **kwargs):
        partner = request.env.user.partner_id.commercial_partner_id
        tasks = request.env['project.task'].sudo().search([
            ('xyz_booking_id', '!=', False), ('partner_id', 'child_of', partner.id),
        ], order='id desc')
        return request.render('xyz_service_core.portal_jobs', {'tasks': tasks})

    @http.route('/my/maintenance/<int:acceptance_id>/pdf', type='http', auth='user', website=True)
    def acceptance_pdf(self, acceptance_id, **kwargs):
        acceptance = request.env['xyz.acceptance'].sudo().browse(acceptance_id).exists()
        if not acceptance or acceptance.task_id.partner_id.commercial_partner_id != request.env.user.partner_id.commercial_partner_id:
            return request.not_found()
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'xyz.acceptance'), ('res_id', '=', acceptance.id), ('mimetype', '=', 'application/pdf'),
        ], limit=1)
        if not attachment:
            return request.not_found()
        import base64
        return request.make_response(base64.b64decode(attachment.datas), headers=[
            ('Content-Type', 'application/pdf'), ('Content-Disposition', 'attachment; filename="acceptance.pdf"'),
        ])
