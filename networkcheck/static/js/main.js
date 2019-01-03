window.onload = () => {
  plotResponseTimes();
  plotGaps();
};

function plotResponseTimes() {
  fetch("api/responsetimes")
    .then(response => {
      if (!response.ok) {
        throw new Error("Error fetching data");
      }
      return response.json()
    })
    .then(results => {
      const meanvals = results.results.map(e => [e[0] * 1000, e[1]]);
      const errors = results.results.map(e => [e[0] * 1000, e[1] - e[2] / 2, e[1] + e[2] / 2]);

      const plotdata = {
        title: {
          text: null,
        },
        xAxis: {
          type: 'datetime',
        },
        yAxis: {
          title: {
            text: "Response time [ms]",
          },
        },
        series: [
          {
            name: "mean",
            type: "spline",
            data: meanvals,
          },
          {
            name: "lower",
            type: "errorbar",
            data: errors,
          },
        ],
        credits: {
          enabled: false,
        },
        plotOptions: {
          spline: {
            color: "#86AEDB",
          },
          errorbar: {
            whiskerLength: 0,
            stemWidth: 3,
            color: "#86AEDB",
          },
        },
      };

      const elem = document.getElementById("plot-response-times");
      const chart = Highcharts.chart(elem, plotdata);
    });
}

function plotGaps() {
  fetch("api/gaps")
    .then(response => {
      if (!response.ok) {
        throw new Error("Error fetching data");
      }
      return response.json()
    })
    .then(results => {
      const gaps = results.results.map(e => [e[0] * 1000, e[1]]);

      const plotdata = {
        chart: {
          type: "scatter"
        },
        title: {
          text: null,
        },
        xAxis: {
          type: 'datetime',
        },
        yAxis: {
          title: {
            text: "Gap between tests [s]",
          },
        },
        series: [
          {
            name: "gaps",
            data: gaps,
          },
        ],
        credits: {
          enabled: false,
        },
        plotOptions: {
          scatter: {
            color: "#86AEDB",
          },
        },
      };

      const elem = document.getElementById("plot-gaps");
      const chart = Highcharts.chart(elem, plotdata);
    });
}
