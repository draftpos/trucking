/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Record } from "@web/model/relational_model/record";

patch(Record.prototype, {
    /**
     * Patch the built-in isRequired function to dynamically apply mandatory fields
     * configured via our JSON dictionary.
     */
    _isRequired(fieldName) {
        // Standard check
        let required = super._isRequired(fieldName);
        if (required) return true;

        if (this.resModel === "trucking.load" && this.data && this.data.mandatory_fields_json) {
            try {
                const mandatoryFields = JSON.parse(this.data.mandatory_fields_json);
                // The frontend validation (red lines) is mainly for "save".
                // Since _isRequired doesn't natively know if a button click triggered it,
                // we'll strictly enforce fields marked for "save".
                if (mandatoryFields.save && mandatoryFields.save.includes(fieldName)) {
                    // One caveat: _isRequired validates the presence in the form.
                    // Make sure the field is actually in the view!
                    if (this.activeFields && this.activeFields[fieldName]) {
                        return true;
                    }
                }
            } catch (e) {
                console.error("Error parsing mandatory_fields_json", e);
            }
        }
        return false;
    }
});
