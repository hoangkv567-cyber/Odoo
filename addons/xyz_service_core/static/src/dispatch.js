/** @odoo-module **/
import { Component, onMounted, onWillUnmount, useRef, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { _t } from '@web/core/l10n/translation';

class XYZDispatch extends Component {
    static template = 'xyz_service_core.Dispatch';
    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.action = useService('action');
        this.board = useRef('board');
        this.filters = useState({area: '', skill: '', areas: [], skills: []});
        onMounted(() => this.load());
        onWillUnmount(() => this.timeline?.destroy());
    }
    async load() {
        const data = await this.orm.call('project.task', 'xyz_dispatch_data', []);
        this.formViewId = data.form_view_id;
        this.filters.areas = [...new Set(data.groups.map(group => group.area).filter(Boolean))];
        this.filters.skills = data.skills;
        this.timeline?.destroy();
        const escape = (value) => { const node = document.createElement('span'); node.textContent = value; return node.innerHTML; };
        const visibleGroups = data.groups.filter(g => (!this.filters.area || g.area === this.filters.area) && (!this.filters.skill || g.skills.includes(Number(this.filters.skill))));
        const groups = [{ id: 0, content: _t('Unassigned') }, ...visibleGroups.map(g => ({...g, content: escape(g.content + (g.area ? ' · ' + g.area : ''))}))];
        const ids = new Set(groups.map(g => g.id));
        const items = data.items.filter(item => ids.has(item.group)).map(item => ({...item, content: escape(item.content), start: item.start.replace(' ', 'T') + 'Z', end: item.end.replace(' ', 'T') + 'Z'}));
        this.timeline = new window.vis.Timeline(this.board.el, items, groups, {
            stack: true, height: '65vh', zoomMin: 3600000, zoomMax: 2678400000,
            editable: { updateTime: true, updateGroup: true, add: false, remove: false },
            onMove: async (item, callback) => {
                try {
                    const format = date => new Date(date).toISOString().slice(0, 19).replace('T', ' ');
                    await this.orm.call('project.task', 'xyz_dispatch_move', [[item.id], item.group, format(item.start), format(item.end)]);
                    callback(item);
                    this.notification.add(_t('Schedule updated'), {type: 'success'});
                } catch (error) {
                    callback(null);
                    this.notification.add(error.data?.message || error.message, {type: 'danger'});
                }
            },
        });
        this.timeline.on('doubleClick', ({item}) => {
            if (item) this.action.doAction({type: 'ir.actions.act_window', res_model: 'project.task', res_id: item, views: [[this.formViewId, 'form']]});
        });
    }
    today() { this.timeline?.moveTo(new Date()); }
    day() { const start = new Date(); start.setHours(0, 0, 0, 0); this.timeline?.setWindow(start, new Date(start.getTime() + 86400000)); }
    week() { const start = new Date(); start.setHours(0, 0, 0, 0); this.timeline?.setWindow(start, new Date(start.getTime() + 7 * 86400000)); }
}
registry.category('actions').add('xyz_dispatch', XYZDispatch);
