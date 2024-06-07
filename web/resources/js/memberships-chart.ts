import ApexCharts from "apexcharts";
import type { ApexOptions } from "apexcharts";
import * as bootstrap from "bootstrap";

const HALF_YEAR = 182 * 24 * 60 * 60 * 1000
const INFINITY = Date.parse("3000-01-01T00:00:00Z")
const fmt = (ms: number): string => {
    let d = new Date(ms);
    d.setSeconds(0, 0)
    // let str = d.toISOString().slice(0, -5)
    // return `<code>${str}Z</code>`
    // "de" because ISO is unreadable in this context (too information dense) and "en" is just cursed
    let str = d.toLocaleString("de")
    return `<code>${str}</code>`
};

function demandElementById<T extends HTMLElement>(id: string): T {
    const el = document.getElementById(id)
    if (el === null) {
        throw new Error(`Element #${id} not found`)
    }
    return el as T
}
const options_: ApexOptions = {
    chart: {
        height: "200px",
        type: 'rangeBar',
        events: {
            // see https://apexcharts.com/docs/options/chart/events/
            click: (_event, _chartContext, w) => {
                console.log(w);
                let { seriesIndex, dataPointIndex } = w;
                let data = w.config.series[seriesIndex].data[dataPointIndex] as Data;

                // console.log(data);
                const ID = "group-detail-modal"
                demandElementById("group-detail-title").innerHTML = `Edit membership #${data.id.toString()}`;

                let { url_edit: urlEdit, url_end: urlEnd } = data.orig_data
                // console.log(actions)
                let elTerm = demandElementById<HTMLAnchorElement>("group-detail-terminate")
                let elEd = demandElementById<HTMLAnchorElement>("group-detail-edit")
                elEd.href = urlEdit
                console.log(urlEnd)

                if (urlEnd !== null) {
                    elTerm.ariaHidden = "false"
                    elTerm.classList.remove("d-none")
                    elTerm.href = urlEnd
                } else {
                    elTerm.ariaHidden = "true"
                    elTerm.classList.add("d-none")
                }
                const modal = new bootstrap.Modal(`#${ID}`, {});
                console.log(modal)
                modal.show();
            },
        },
    },
    plotOptions: {
        bar: {
            horizontal: true,
            rangeBarGroupRows: true,
        }
    },
    xaxis: {
        type: 'datetime',
        max: new Date().getTime() + HALF_YEAR,
        tooltip: {enabled: true},
    },
    annotations: {
        xaxis: [
            // We could add lots of lines here (tasks, membership start, …).
            { x: new Date().getTime(), label: { text: "today" }, },
        ]
    },
    stroke: {
        show: true,
        curve: 'straight',
        lineCap: 'butt',
        colors: undefined,
        width: 2, // this is important: otherwise we might not see e.g. small blockages
        dashArray: 0, 
    },
    tooltip: {
        custom: ({ctx, series, seriesIndex, dataPointIndex, w}) => {
            let data = w.config.series[seriesIndex].data[dataPointIndex] as Data
            let [since, until] = data.y
            let range_desc = data.ends_unbounded
                ? `since <i class="fa-solid fa-right-from-bracket"></i> ${fmt(since)}`
                : `from <i class="fa-solid fa-right-from-bracket"></i> ${fmt(since)}
                   <br> to <i class="fa-solid fa-right-to-bracket"></i> ${fmt(until)}`
            return `
              <div class="card">
                <div class="card-body p-2">
                  <div class="fw-bold fs-5 mb-1">${data.x}</div>
                  <p class="card-text fs-6">${range_desc}</p>
                  <!-- <a href="#" class="btn btn-primary">Go somewhere</a> -->
              </div>
            `
        }
    },
};

document.addEventListener('DOMContentLoaded', () => {
    const id = "memberships-timeline";
    const el = document.getElementById(id);
    if (el === null) {
        console.error(`no element with id ${id} found`);
        return;
    }
    fetch(el.dataset.url!)
        .then(resp => resp.json())
        .catch(console.error)
        .then(j => {
            const data = parseResponse(j);
            console.log(data)
            let chart = new ApexCharts(
                el,
                {
                    ...options_, 
                    series: [
                        {data},
                    ],
                } 
            )
            chart.render()
        })
})

type Data = {
    x: string
    y: [number, number]
    begins_unbounded: boolean
    ends_unbounded: boolean
    id: number,
    orig_data: any,
}
function parseResponse(j: any): Data[] {
    // schema for `j`: see `user_show_groups_json`
    return j.items?.map(mem => ({
        x: mem.group_name,
        y: [
            new Date(mem.begins_at.timestamp * 1000).getTime(),
            mem.ends_at.timestamp ? new Date(mem.ends_at.timestamp * 1000) : INFINITY,
        ],
        begins_unbounded: mem.begins_at.timestamp == null,
        ends_unbounded: mem.ends_at.timestamp == null,
        id: mem.id,
        orig_data: mem,
    } as Data))
}

