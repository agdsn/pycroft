// see: https://www.typescriptlang.org/docs/handbook/declaration-files/templates/module-class-d-ts.html

/**
 * These declarations roughly follow the statements from the docs[1].
 *
 * [1] https://github.com/twitter/typeahead.js/blob/v0.11.1/doc/bloodhound.md
 */
declare module 'typeahead.js/dist/bloodhound' {
    export = Bloodhound;

    /**
     * Test
     */
    declare class Bloodhound {
        constructor(options?: BloodhoundOptions);

        VERSION: string;
        static tokenizers: {
            nonword: Tokenizer,
            whitespace: Tokenizer,
            obj: {
                nonword(keys: Array<string>): (o: object) => string,
                whitespace(keys: Array<string>): (o: object) => string,
            }
        };

        static noConflict(): Bloodhound;

        initialize(reinitialize?: boolean): Promise<any>;

        add(data: any): void;

        get(ids: any[]): void;

        search(query: any, sync: any, async: any): any[];

        clear(): void;

        ttAdapter(): any;
    }

    interface Tokenizer extends Function {
        (token: string): string[];
    }

    /**
     * These things can serve as compare functions for `sort`.
     *
     * [1] https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort#parameters
     */
    interface CompareFunction<T> extends Function {
        (firstEl: T, secondEl: T): number,
    }

    interface BloodhoundOptions {
        datumTokenizer(query: any): string[],

        queryTokenizer(datum: any): string[],

        initialize?: boolean,

        identify?(datum: any): string,

        sufficient?: number,
        sorter?: CompareFunction<any>,
        local?: any[] | (() => any[]),
        prefetch?: URL | PrefetchOptions,
        remote?: URL | RemoteOptions,
    }

    interface PrefetchOptions {
        url: URL | string,
        cache?: boolean,
        ttl?: number,
        cacheKey?: URL,
        thumbprint?: string,

        prepare?<T>(settings: T): T,

        transform?<T>(response: T): T,
    }

    interface RemoteOptions {
        url: URL | string,

        prepare?<T>(query: any, settings: T): T,

        wildcard?: string,
        rateLimitBy?: 'debounce' | 'throttle',
        rateLimitWait?: number,

        transform(response: any): any,
    }
}
