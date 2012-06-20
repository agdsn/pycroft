/**
 * Created with PyCharm.
 * User: nick-xyz-
 * Date: 6/20/12
 * Time: 8:59 PM
 * To change this template use File | Settings | File Templates.
 */
function parseDateFormat(format){
    var separator = format.match(/[.\/-].*?/),
            parts = format.split(/\W+/);
    if (!separator || !parts || parts.length == 0){
        throw new Error("Invalid date format.");
    }
    return {separator: separator, parts: parts};
}

function formatDate(date, format){
    var val = {
        d: date.getDate(),
        m: date.getMonth() + 1,
        yy: date.getFullYear().toString().substring(2),
        yyyy: date.getFullYear()
    };
    val.dd = (val.d < 10 ? '0' : '') + val.d;
    val.mm = (val.m < 10 ? '0' : '') + val.m;
    var date = [];
    for (var i=0, cnt = format.parts.length; i < cnt; i++) {
        date.push(val[format.parts[i]]);
    }
    return date.join(format.separator);
}