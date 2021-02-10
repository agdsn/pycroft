interface JQuery<Element> {
    autocomplete(options: AutocompleteOptions,
                 ...datasets: DataSet<any>[]): JQuery<Element>;
}

/**
 * Following https://github.com/algolia/autocomplete.js#global-options
 */
interface AutocompleteOptions {
    autoselect?: boolean;
    autoselectOnBlur?: boolean;
    tabAutocomplete?: boolean;
    hint?: boolean;
    debug?: boolean;
    openOnFocus?: boolean;
    appendTo?: HTMLElementTagNameMap | string;
    dropdownMenuContainer?: HTMLElementTagNameMap | string;
    templates?: TemplateOptions;
    cssClasses?: CssClassesOptions;
    keyboardShortcuts?: string[];
    ariaLabel?: string;
    minLength?: number;
    autoWidth?: boolean;
}

interface TemplateOptions {
    dropdownMenu?: string;
    header?: string;
    footer?: string;
    empty?: string;
}

interface CssClassesOptions {
    root?: string;
    prefix?: string;
    noPrefix?: string;
    dropdownMenu?: string;
    input?: string;
    hint?: string;
    suggestions?: string;
    suggestion?: string;
    cursor?: string;
    dataset?: string;
    empty?: string;
}

interface DataSet<TSuggestion> {
    source?(query, cb): void;
    name?: string;
    displayKey?(suggestion: TSuggestion): string;
    templates?: {
        empty?: string | PrecompiledTemplate;
        footer?: string | PrecompiledTemplate;
        header?: string | PrecompiledTemplate;
        suggestion?(suggestion: TSuggestion, ...args: any): string;
    };
    debounce?: number;
    cache?: boolean;
}

interface PrecompiledTemplate {
    ({query: string, isEmpty: bool}, ...args: any): string;
}
