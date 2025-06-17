// my_fleet_restrict_stages/static/src/js/fleet_kanban_controller.js
/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FleetRestrictedKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.user = useService("user");

        // Cargar las etapas restringidas y los grupos de usuarios autorizados
        this.restrictedStageIds = [];
        this.allowedGroupIds = [];
        this._loadRestrictions();
    }

    async _loadRestrictions() {
        // Carga las etapas que están marcadas como 'is_restricted_stage = True'
        this.restrictedStageIds = await this.orm.searchRead(
            'fleet.vehicle.stage',
            [['is_restricted_stage', '=', True]],
            ['id']
        );
        this.restrictedStageIds = this.restrictedStageIds.map(stage => stage.id);

        // Define aquí los IDs externos de los grupos que SÍ pueden arrastrar a las etapas restringidas.
        // Ejemplo: 'base.group_system' para administradores, 'fleet.group_fleet_manager' para gestores de flota
        // Puedes parametrizar esto más adelante con un modelo de configuración si es necesario.
        const allowedGroupXmlIds = ['base.group_system', 'fleet.group_fleet_manager']; // Ejemplo

        for (const xml_id of allowedGroupXmlIds) {
            try {
                const group = await this.orm.call(
                    'ir.model.data',
                    'check_external_id',
                    [xml_id]
                );
                this.allowedGroupIds.push(group[1]); // group[1] es el ID del registro
            } catch (e) {
                console.warn(`Could not find external ID for group: ${xml_id}`, e);
            }
        }
    }

    /**
     * Override the onWillDropRecord method to prevent dropping into restricted stages.
     * This method is called before a record is actually dropped.
     * @param {Object} args
     * @param {Object} args.record - The record being dragged
     * @param {Object} args.column - The target column/stage
     * @returns {boolean} True if the drop is allowed, False otherwise.
     */
    onWillDropRecord(args) {
        const { record, column } = args;
        const targetStageId = column.resId; // resId es el ID de la etapa

        // Si la etapa de destino NO es una etapa restringida, siempre se permite el arrastre
        if (!this.restrictedStageIds.includes(targetStageId)) {
            return super.onWillDropRecord(args);
        }

        // Si la etapa de destino ES una etapa restringida, comprobamos los permisos del usuario
        const currentUserGroups = this.user.groups.map(group => group.id);
        const isUserAllowed = this.allowedGroupIds.some(allowedGroupId =>
            currentUserGroups.includes(allowedGroupId)
        );

        if (!isUserAllowed) {
            this.notification.add("No tiene permisos para mover elementos a esta etapa restringida.", { type: "danger" });
            return false; // Previene el arrastre
        }

        return super.onWillDropRecord(args); // Permite el arrastre si el usuario tiene permisos
    }

    /**
     * Override the onWillDropGroup method if you also want to restrict reordering of columns/stages.
     * Note: Restricting column reordering (drag and drop of columns themselves) is usually handled
     * by `records_draggable="false"` on the kanban tag for all stages, or by more complex JS logic.
     * For now, we focus on record dragging.
     */
    // onWillDropGroup(args) {
    //     // Lógica para restringir el arrastre de columnas si es necesario
    //     return super.onWillDropGroup(args);
    // }
}

FleetRestrictedKanbanController.template = "my_fleet_restrict_stages.FleetKanbanView";

registry.category("views").add("fleet_restricted_kanban", kanbanView);