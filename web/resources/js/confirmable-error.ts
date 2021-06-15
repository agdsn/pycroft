document.addEventListener('DOMContentLoaded', () => {
    hideAllConfirmationCheckboxes();
    exposeCheckboxesForErrors();
    hideFormGroupsWithHiddenInput();
})


/**
 * Hide all `data-role=confirm-checkbox` checkboxes by default.
 */
function hideAllConfirmationCheckboxes() {
    document.querySelectorAll('[data-role=confirm-checkbox]')
        .forEach(el => (<HTMLElement>el).hidden = true);
}


/**
 * Expose all `data-role=confirm-checkbox` checkboxes as soon as they are
 * referenced by a `data-role=confirmable-error` element.
 */
function exposeCheckboxesForErrors() {
    document.querySelectorAll('[data-role=confirmable-error]')
        .forEach(errorEl => {
            const {confirmedByCheckboxId: cbId} = (<HTMLElement>errorEl).dataset;
            if (cbId == undefined) {
                console.error(`Element ${errorEl} does not have data-confirmed-by-checkbox-id set`)
                return;
            }
            const checkBox = document.getElementById(<string>cbId);

            if (checkBox == null) {
                console.error(`There is no checkbox with id #${cbId}!`)
                return;
            }
            if (checkBox!.dataset.role != 'confirm-checkbox') {
                console.warn(`Referenced confirm checkbox #${cbId}`
                    + ' does not have data-role="confirm-checkbox" set');
            }
            checkBox!.hidden = false;
        });
}


/**
 * For all hidden checkboxes, hide their surrounding form-group as well.
 */
function hideFormGroupsWithHiddenInput() {
    document.querySelectorAll('form [data-role=confirm-checkbox]')
        .forEach(el => {
            const checkbox = <HTMLElement>el;
            const formGroup = document.getElementById(`form-group-${el.id}`)!;
            formGroup.hidden = checkbox.hidden;
        })
}
