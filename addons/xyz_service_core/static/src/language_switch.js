/** @odoo-module **/
import { Component, onWillStart, useState } from '@odoo/owl';
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { user } from '@web/core/user';
import { useService } from '@web/core/utils/hooks';

/**
 * Top-bar language switcher: writes `res.users.lang` for the current user and reloads the
 * page, because the whole backend (labels, views, reports) is rendered from that language.
 */
export class XYZLanguageSwitcher extends Component {
    static template = 'xyz_service_core.LanguageSwitcher';
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.user = user;
        this.state = useState({languages: []});
        onWillStart(async () => {
            this.state.languages = await this.orm.searchRead(
                'res.lang', [['active', '=', true]], ['code', 'name'], {order: 'name'}
            );
        });
    }

    get currentLanguage() {
        // `user.lang` is the browser locale (vi-VN), the context keeps the Odoo code (vi_VN).
        const code = this.user.context.lang;
        return this.state.languages.find((lang) => lang.code === code) || {code, name: code};
    }

    get shortCode() {
        return this.currentLanguage.code.split('_')[0].toUpperCase();
    }

    async selectLanguage(code) {
        if (code === this.user.context.lang) {
            return;
        }
        await this.orm.write('res.users', [this.user.userId], {lang: code});
        this.notification.add(_t('Language updated, reloading the page…'), {type: 'info'});
        window.location.reload();
    }
}

export const systrayItem = {Component: XYZLanguageSwitcher};

registry.category('systray').add('xyz_language_switcher', systrayItem, {sequence: 2});
