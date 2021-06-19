interface JQuery<Element> {
    /** Refresh the table's contents.
     *
     * @param method
     * @param params Additional parameters (not completely typed,
     * see [docs](https://bootstrap-table.com/docs/api/methods/#refresh))
     */
    bootstrapTable(method: 'refresh', params?: { [key: string]: any }): JQuery<Element>;
}
