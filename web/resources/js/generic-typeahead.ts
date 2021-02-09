import $ from 'jquery';
import Bloodhound from 'typeahead.js/dist/bloodhound';
import 'autocomplete.js/src/jquery/plugin'

/** A function setting up generic completion against some lookup URL.
 *
 * The lookup URL shoud accept the input in the `query=`-GET-Parameter and
 * respond with a json of the following form:
 *
 * ```json
 * {
 *     items: [
 *         "suggestion1",
 *         "suggestion2",
 *         // …
 *         "suggestionn"
 *     ]
 * }
 * ```
 *
 * @param elem The input element.  Should provide `data-typeahead-url` and `data-typeahead-name`.
 */
export function create_dataset(elem: HTMLElement) {
    const { typeaheadUrl: url, typeaheadName: datasetName } = elem.dataset;
    console.log(`Setting up typeahead autocompletion '${datasetName}' (remote: ${url})`)

    const bloodhound = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.whitespace,
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: `${url}?query=%QUERY`,
            // unfortunately, this thing does not have any error handling.
            transform: (response: { items: any; }) => response.items,
            wildcard: '%QUERY',
        }
    });

    return {
        name: datasetName,
        displayKey: (x: string) => x,
        source: (query: any, cb: any) => bloodhound.ttAdapter()(query, cb, cb),
        templates: {
            empty: '<span class="disabled">Keine Ergebnisse</span>',
        }
    };

}

const options = {
    hint: true,
    minLength: 1,
};

console.log("Loaded `generic-typeahead.ts`")
document.addEventListener('DOMContentLoaded', () => {
    console.log("Dom content loaded!")
    document.querySelectorAll('[data-role=generic-typeahead]')
        .forEach(elem => {
            $(elem).autocomplete(options, create_dataset(elem as HTMLElement))
        })
})
