(function () {
  "use strict";

  /*
   * NexGrid AI dashboard
   * ---------------------
   * The UI deliberately keeps a complete demo dataset in the client. This makes
   * the page useful in a static preview while still allowing the FastAPI service
   * to replace any part of the dataset when /api/dashboard is available.
   */

  var API_TIMEOUT_MS = 4500;
  var REFRESH_INTERVAL_MS = 30000;
  var SVG_NS = "http://www.w3.org/2000/svg";

  var DEMO_DATA = {
    meta: {
      status: "operational",
      last_updated: "2026-10-01T14:32:18Z",
      source: "seeded-demo",
      workspace: "Metro Fleet"
    },
    kpis: {
      fleet_soc: { value: 72, trend: 4.8, direction: "up", detail: "17 of 24 vehicles above departure target" },
      grid_load: { value: 1.84, unit: "MW", trend: 12.6, direction: "down", detail: "22% below site import limit" },
      renewable_share: { value: 64, trend: 8.2, direction: "up", detail: "Solar + battery discharge today" },
      projected_savings: { value: 1284, trend: 18.4, direction: "up", detail: "This month · versus unmanaged charging" },
      carbon_avoided: { value: 2.7, unit: "t", trend: 11.1, direction: "up", detail: "Equivalent to 6,820 km not driven" }
    },
    energy: {
      labels: ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "00:00"],
      demand: [1.12, 1.02, 0.94, 1.28, 1.92, 2.06, 2.17, 2.02, 2.29, 3.05, 2.58, 1.72, 1.34],
      solar: [0, 0, 0, 0.08, 0.35, 0.86, 1.18, 1.02, 0.57, 0.12, 0, 0, 0],
      battery: [0.05, 0.04, 0.03, 0.02, -0.1, -0.28, -0.45, -0.42, -0.22, -0.62, -0.45, -0.12, 0.02],
      upper: [1.28, 1.18, 1.12, 1.5, 2.14, 2.3, 2.43, 2.3, 2.59, 3.37, 2.88, 1.98, 1.52],
      lower: [0.96, 0.88, 0.78, 1.06, 1.7, 1.82, 1.91, 1.74, 1.99, 2.73, 2.28, 1.46, 1.16],
      forecast_demand: [1.1, 1.0, 0.94, 1.3, 1.9, 2.08, 2.18, 2.04, 2.31, 3.0, 2.55, 1.7, 1.3],
      forecast_solar: [0, 0, 0, 0.07, 0.39, 0.9, 1.21, 1.07, 0.6, 0.1, 0, 0, 0],
      forecast_battery: [0.04, 0.03, 0.02, 0.02, -0.08, -0.31, -0.48, -0.4, -0.2, -0.65, -0.42, -0.1, 0.02],
      current_index: 7,
      peak_import: 2.42,
      peak_import_time: "18:00",
      peak_import_delta: "−18% vs baseline",
      solar_window: "10:00 — 16:00",
      solar_window_detail: "1.18 MWh available to shift",
      next_decision: "in 18 min",
      confidence: 94
    },
    flow: {
      solar_kw: 412,
      solar_trend: "↑ 18% today",
      grid_kw: 1840,
      grid_status: "Import · stable",
      battery_kw: 620,
      battery_status: "Discharging · 78%",
      fleet_kw: 2872,
      fleet_status: "24 active sessions",
      balance_status: "Balanced",
      balance_detail: "within policy"
    },
    recommendation: {
      id: "rec-solar-shift-20261001",
      title: "Shift 6 flexible vans into solar window",
      summary: "Pre-charge the North Harbor pool from 10:15–13:45 while onsite PV is abundant, then hold the battery for the 18:00 tariff spike.",
      savings: "$38.40",
      peak_reduction: "−420 kW",
      carbon: "86 kg",
      confidence: 94,
      reasons: [
        "9 vehicles have flexible departure windows",
        "PV forecast is above the 7-day median",
        "Reserve floor remains protected at 30%"
      ],
      guardrail: "No vehicle will leave below its configured departure target.",
      agent: "Dispatch agent v2.4",
      age: "just now"
    },
    fleet: {
      total: 24,
      vehicles: [
        { id: "EV-204", model: "Ford E-Transit", site: "North Harbor", soc: 82, target: 90, range: 188, status: "charging", eta: "00:42", departure: "07:30", power: 88, priority: "Routine", health: 97 },
        { id: "EV-118", model: "Rivian EDV 700", site: "North Harbor", soc: 96, target: 90, range: 224, status: "ready", eta: "Ready", departure: "06:45", power: 0, priority: "Ready", health: 99 },
        { id: "EV-307", model: "Mercedes eSprinter", site: "East Yard", soc: 54, target: 80, range: 121, status: "charging", eta: "01:18", departure: "08:00", power: 72, priority: "Routine", health: 94 },
        { id: "EV-091", model: "Ford F-150 Lightning", site: "South Loop", soc: 31, target: 70, range: 86, status: "attention", eta: "02:06", departure: "06:10", power: 42, priority: "Priority", health: 92 },
        { id: "EV-226", model: "Chevrolet BrightDrop", site: "West Campus", soc: 88, target: 85, range: 196, status: "ready", eta: "Ready", departure: "09:15", power: 0, priority: "Ready", health: 98 },
        { id: "EV-142", model: "Rivian EDV 500", site: "East Yard", soc: 67, target: 85, range: 148, status: "charging", eta: "00:54", departure: "07:50", power: 64, priority: "Routine", health: 96 },
        { id: "EV-255", model: "Ford E-Transit", site: "North Harbor", soc: 48, target: 80, range: 108, status: "paused", eta: "01:44", departure: "08:30", power: 0, priority: "Flexible", health: 95 },
        { id: "EV-333", model: "Mercedes eSprinter", site: "South Loop", soc: 75, target: 80, range: 169, status: "charging", eta: "00:27", departure: "07:00", power: 91, priority: "Routine", health: 93 }
      ]
    },
    agents: [
      { time: "now", title: "Dispatch agent updated the charge plan", text: "Held 420 kW of battery capacity for the 18:00 price boundary.", tone: "violet", icon: "✦" },
      { time: "2m", title: "Forecast agent validated PV uplift", text: "Solar generation is tracking 18% above the 7-day median.", tone: "green", icon: "↗" },
      { time: "6m", title: "Safety agent checked departure constraints", text: "18 of 18 policy checks passed; no route commitment changed.", tone: "orange", icon: "⬡" },
      { time: "11m", title: "Telemetry agent resolved a stale signal", text: "Charger NH-04 returned to the live stream.", tone: "green", icon: "◌" }
    ],
    monitoring: {
      overall: "Healthy",
      freshness_seconds: 12,
      freshness_percent: 92,
      completeness: 99.2,
      completeness_detail: "1,842 / 1,857 signals received",
      confidence: 94,
      drift: 0.8,
      model_version: "dispatch-forecast-v2.4",
      evaluated: "14 min ago",
      policy_checks: "18 / 18 pass"
    }
  };

  var state = {
    data: clone(DEMO_DATA),
    usingFallback: true,
    apiStatus: { dashboard: false, monitoring: false },
    bannerDismissed: false,
    chartMode: "live",
    fleetFilter: "all",
    fleetSearch: "",
    fleetPage: 0,
    selectedFeedback: null,
    optimizationRunning: false,
    recommendationDismissed: false,
    lastSync: null,
    previousFocus: null
  };

  var $ = function (selector, root) {
    return (root || document).querySelector(selector);
  };

  var $$ = function (selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function merge(base, incoming) {
    if (Array.isArray(incoming)) {
      return incoming.slice();
    }
    if (!isObject(incoming)) {
      return incoming === undefined || incoming === null ? base : incoming;
    }
    var result = isObject(base) ? clone(base) : {};
    Object.keys(incoming).forEach(function (key) {
      if (isObject(incoming[key]) && isObject(result[key])) {
        result[key] = merge(result[key], incoming[key]);
      } else if (incoming[key] !== undefined && incoming[key] !== null) {
        result[key] = incoming[key];
      }
    });
    return result;
  }

  function firstDefined() {
    for (var i = 0; i < arguments.length; i += 1) {
      if (arguments[i] !== undefined && arguments[i] !== null && arguments[i] !== "") {
        return arguments[i];
      }
    }
    return undefined;
  }

  function path(object, paths, fallback) {
    for (var i = 0; i < paths.length; i += 1) {
      var parts = paths[i].split(".");
      var current = object;
      var found = true;
      for (var j = 0; j < parts.length; j += 1) {
        if (current === null || current === undefined || current[parts[j]] === undefined) {
          found = false;
          break;
        }
        current = current[parts[j]];
      }
      if (found && current !== null && current !== undefined && current !== "") {
        return current;
      }
    }
    return fallback;
  }

  function numberValue(value, fallback) {
    if (isObject(value)) {
      value = firstDefined(value.value, value.amount, value.current, value.result);
    }
    var parsed = typeof value === "number" ? value : parseFloat(String(value).replace(/[^0-9.\-]/g, ""));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function stringValue(value, fallback) {
    if (value === undefined || value === null) return fallback || "";
    if (isObject(value)) return stringValue(firstDefined(value.label, value.name, value.value), fallback);
    return String(value);
  }

  function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatNumber(value, decimals) {
    var parsed = numberValue(value, 0);
    return parsed.toLocaleString(undefined, {
      minimumFractionDigits: decimals === undefined ? 0 : decimals,
      maximumFractionDigits: decimals === undefined ? 0 : decimals
    });
  }

  function formatCurrency(value) {
    var parsed = numberValue(value, 0);
    return parsed.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  }

  function setText(id, value) {
    var element = document.getElementById(id);
    if (element) element.textContent = value === undefined || value === null ? "—" : String(value);
  }

  function setWidth(id, value) {
    var element = document.getElementById(id);
    if (!element) return;
    var safe = Math.max(0, Math.min(100, numberValue(value, 0)));
    element.style.width = safe + "%";
  }

  function normalizePayload(payload) {
    var incoming = payload;
    if (incoming && isObject(incoming)) {
      incoming = firstDefined(incoming.dashboard, incoming.data, incoming.result, incoming.payload, incoming);
    }
    if (!isObject(incoming)) incoming = {};

    var normalized = merge(DEMO_DATA, incoming);
    normalized.kpis = normalized.kpis || {};
    normalized.energy = normalized.energy || {};
    normalized.flow = normalized.flow || {};
    normalized.recommendation = normalized.recommendation || {};
    normalized.monitoring = normalized.monitoring || {};

    /* Accommodate compact FastAPI responses as well as the richer demo shape. */
    var kpis = incoming.kpis || {};
    normalized.kpis.fleet_soc = firstDefined(kpis.fleet_soc, kpis.fleetSoc, incoming.fleet_soc, incoming.fleetSoc, normalized.kpis.fleet_soc);
    normalized.kpis.grid_load = firstDefined(kpis.grid_load, kpis.gridLoad, incoming.grid_load, incoming.gridLoad, normalized.kpis.grid_load);
    normalized.kpis.renewable_share = firstDefined(kpis.renewable_share, kpis.renewableShare, incoming.renewable_share, incoming.renewableShare, normalized.kpis.renewable_share);
    normalized.kpis.projected_savings = firstDefined(kpis.projected_savings, kpis.projectedSavings, incoming.projected_savings, incoming.projectedSavings, normalized.kpis.projected_savings);
    normalized.kpis.carbon_avoided = firstDefined(kpis.carbon_avoided, kpis.carbonAvoided, incoming.carbon_avoided, incoming.carbonAvoided, normalized.kpis.carbon_avoided);

    var energy = incoming.energy || incoming.chart || {};
    if (isObject(energy)) {
      normalized.energy.labels = firstDefined(energy.labels, energy.timestamps, energy.times, normalized.energy.labels);
      normalized.energy.demand = firstDefined(energy.demand, energy.load, energy.site_demand, normalized.energy.demand);
      normalized.energy.solar = firstDefined(energy.solar, energy.solar_generation, energy.generation, normalized.energy.solar);
      normalized.energy.battery = firstDefined(energy.battery, energy.battery_dispatch, normalized.energy.battery);
      normalized.energy.upper = firstDefined(energy.upper, energy.confidence_upper, normalized.energy.upper);
      normalized.energy.lower = firstDefined(energy.lower, energy.confidence_lower, normalized.energy.lower);
      normalized.energy.current_index = firstDefined(energy.current_index, energy.now_index, normalized.energy.current_index);
    }

    var fleet = firstDefined(incoming.fleet, incoming.vehicles, normalized.fleet);
    normalized.fleet = Array.isArray(fleet) ? { total: fleet.length, vehicles: fleet } : merge(normalized.fleet, fleet || {});
    if (!Array.isArray(normalized.fleet.vehicles)) normalized.fleet.vehicles = clone(DEMO_DATA.fleet.vehicles);
    normalized.fleet.total = numberValue(firstDefined(normalized.fleet.total, incoming.fleet_total), normalized.fleet.vehicles.length || 24);

    var monitoring = incoming.monitoring || incoming.quality || {};
    normalized.monitoring.freshness_seconds = firstDefined(monitoring.freshness_seconds, monitoring.freshness, monitoring.data_freshness, normalized.monitoring.freshness_seconds);
    normalized.monitoring.completeness = firstDefined(monitoring.completeness, monitoring.telemetry_completeness, normalized.monitoring.completeness);
    normalized.monitoring.confidence = firstDefined(monitoring.confidence, monitoring.forecast_confidence, normalized.monitoring.confidence);
    normalized.monitoring.drift = firstDefined(monitoring.drift, monitoring.model_drift, normalized.monitoring.drift);

    return normalized;
  }

  function apiRequest(url, options) {
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller ? window.setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS) : null;
    var requestOptions = options || {};
    requestOptions.headers = Object.assign({ Accept: "application/json" }, requestOptions.headers || {});
    if (controller) requestOptions.signal = controller.signal;

    return window.fetch(url, requestOptions).then(function (response) {
      if (!response.ok) throw new Error("Request failed (" + response.status + ")");
      return response.text().then(function (text) {
        if (!text) return {};
        try {
          return JSON.parse(text);
        } catch (error) {
          throw new Error("The service returned invalid JSON");
        }
      });
    }).finally(function () {
      if (timer) window.clearTimeout(timer);
    });
  }

  function showToast(message, type, duration) {
    var region = $("#toastRegion");
    if (!region) return;
    var toast = document.createElement("div");
    toast.className = "toast " + (type || "");
    var icon = type === "error" ? "!" : type === "warning" ? "◌" : "✓";
    toast.innerHTML = '<span class="toast-icon" aria-hidden="true">' + icon + '</span><span>' + escapeHtml(message) + "</span>";
    region.appendChild(toast);
    window.setTimeout(function () {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(8px)";
      window.setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 180);
    }, duration || 3800);
  }

  function renderDataSource() {
    var banner = $("#demoBanner");
    if (!banner) return;
    if (state.usingFallback && !state.bannerDismissed) banner.classList.remove("hidden");
    else banner.classList.add("hidden");
    var syncLabel = state.usingFallback ? "demo snapshot" : "synced just now";
    setText("lastSynced", syncLabel);
  }

  function renderKpis() {
    var kpis = state.data.kpis || {};
    var fleetSoc = kpis.fleet_soc || {};
    var gridLoad = kpis.grid_load || {};
    var renewable = kpis.renewable_share || {};
    var savings = kpis.projected_savings || {};
    var carbon = kpis.carbon_avoided || {};

    var soc = numberValue(fleetSoc, 72);
    var grid = numberValue(gridLoad, 1.84);
    var renew = numberValue(renewable, 64);
    var saved = numberValue(savings, 1284);
    var carbonValue = numberValue(carbon, 2.7);

    setText("kpiFleetSoc", formatNumber(soc) + "%");
    setText("kpiFleetSocTrend", trendText(fleetSoc, "4.8%"));
    setText("kpiFleetSocDetail", stringValue(path(fleetSoc, ["detail", "description"], null), "17 of 24 vehicles above departure target"));
    setWidth("kpiFleetSocMeter", soc);

    setText("kpiGridLoad", grid.toFixed(2) + " MW");
    setText("kpiGridTrend", trendText(gridLoad, "12.6%", true));
    setText("kpiGridDetail", stringValue(path(gridLoad, ["detail", "description"], null), "22% below site import limit"));

    setText("kpiRenewable", formatNumber(renew) + "%");
    setText("kpiRenewableTrend", trendText(renewable, "8.2%"));
    setText("kpiRenewableDetail", stringValue(path(renewable, ["detail", "description"], null), "Solar + battery discharge today"));
    setWidth("kpiRenewableMeter", renew);

    setText("kpiSavings", formatCurrency(saved));
    setText("kpiSavingsTrend", trendText(savings, "18.4%"));
    setText("kpiSavingsDetail", stringValue(path(savings, ["detail", "description"], null), "This month · versus unmanaged charging"));

    setText("kpiCarbon", carbonValue.toFixed(1) + " t");
    setText("kpiCarbonTrend", trendText(carbon, "11.1%"));
    setText("kpiCarbonDetail", stringValue(path(carbon, ["detail", "description"], null), "Equivalent to 6,820 km not driven"));
  }

  function trendText(metric, fallback, invert) {
    var value = isObject(metric) ? numberValue(firstDefined(metric.trend, metric.delta, metric.change), numberValue(fallback, 0)) : numberValue(fallback, 0);
    var direction = isObject(metric) ? stringValue(firstDefined(metric.direction, metric.trend_direction), "") : "";
    if (!direction) direction = invert ? "down" : "up";
    return (direction.toLowerCase() === "down" ? "↓ " : "↑ ") + Math.abs(value).toFixed(1) + "%";
  }

  function renderFlow() {
    var flow = state.data.flow || {};
    setText("flowSolar", formatNumber(numberValue(flow.solar_kw, 412)) + " kW");
    setText("flowGrid", formatNumber(numberValue(flow.grid_kw, 1840)) + " kW");
    setText("flowBattery", formatNumber(numberValue(flow.battery_kw, 620)) + " kW");
    setText("flowFleet", formatNumber(numberValue(flow.fleet_kw, 2872)) + " kW");

    var solarStatus = $("#flowSolar", null);
    if (solarStatus && solarStatus.parentNode) {
      var em = solarStatus.parentNode.querySelector("em");
      if (em) em.textContent = stringValue(flow.solar_trend, "↑ 18% today");
    }
    var gridStatus = $("#flowGrid", null);
    if (gridStatus && gridStatus.parentNode) {
      var gridEm = gridStatus.parentNode.querySelector("em");
      if (gridEm) gridEm.textContent = stringValue(flow.grid_status, "Import · stable");
    }
    var batteryStatus = $("#flowBattery", null);
    if (batteryStatus && batteryStatus.parentNode) {
      var batteryEm = batteryStatus.parentNode.querySelector("em");
      if (batteryEm) batteryEm.textContent = stringValue(flow.battery_status, "Discharging · 78%");
    }
    var fleetStatus = $("#flowFleet", null);
    if (fleetStatus && fleetStatus.parentNode) {
      var fleetEm = fleetStatus.parentNode.querySelector("em");
      if (fleetEm) fleetEm.textContent = stringValue(flow.fleet_status, "24 active sessions");
    }
    var balance = $(".flow-status");
    if (balance) {
      var balanceStrong = balance.querySelector("strong");
      var balanceSmall = balance.querySelector("small");
      if (balanceStrong) balanceStrong.textContent = stringValue(flow.balance_status, "Balanced");
      if (balanceSmall) balanceSmall.textContent = stringValue(flow.balance_detail, "within policy");
    }
  }

  function renderRecommendation() {
    var recommendation = state.data.recommendation || {};
    var title = stringValue(firstDefined(recommendation.title, recommendation.headline), DEMO_DATA.recommendation.title);
    var summary = stringValue(firstDefined(recommendation.summary, recommendation.description, recommendation.explanation), DEMO_DATA.recommendation.summary);
    var confidence = numberValue(firstDefined(recommendation.confidence, recommendation.score), DEMO_DATA.recommendation.confidence);
    var reasons = firstDefined(recommendation.reasons, recommendation.reasoning, DEMO_DATA.recommendation.reasons);
    if (!Array.isArray(reasons)) reasons = [String(reasons)];

    setText("recommendationTitle", title);
    setText("recommendationSummary", summary);
    setText("recommendationSavings", stringValue(firstDefined(recommendation.savings, recommendation.estimated_savings), DEMO_DATA.recommendation.savings));
    setText("recommendationPeak", stringValue(firstDefined(recommendation.peak_reduction, recommendation.peak_reduction_kw), DEMO_DATA.recommendation.peak_reduction));
    setText("recommendationCarbon", stringValue(firstDefined(recommendation.carbon, recommendation.carbon_avoided), DEMO_DATA.recommendation.carbon));
    setText("recommendationConfidence", Math.round(confidence) + "%");
    setWidth("recommendationConfidenceBar", confidence);
    setText("recommendationAge", stringValue(recommendation.age, "just now"));

    var list = $("#recommendationReasons");
    if (list) {
      list.innerHTML = reasons.slice(0, 4).map(function (reason) {
        return '<li><span class="reason-check">✓</span> ' + escapeHtml(reason) + "</li>";
      }).join("");
    }
    var guardrail = $(".guardrail-callout");
    if (guardrail) {
      var guardrailText = guardrail.querySelector("span:last-child");
      if (guardrailText) guardrailText.innerHTML = "<strong>Guardrail active.</strong> " + escapeHtml(stringValue(recommendation.guardrail, DEMO_DATA.recommendation.guardrail));
    }

    var panel = $("#recommendationPanel");
    if (panel) panel.classList.toggle("recommendation-dismissed", state.recommendationDismissed);
  }

  function getEnergyArrays() {
    var energy = state.data.energy || {};
    var labels = Array.isArray(energy.labels) && energy.labels.length ? energy.labels : DEMO_DATA.energy.labels;
    var demandKey = state.chartMode === "forecast" ? "forecast_demand" : "demand";
    var solarKey = state.chartMode === "forecast" ? "forecast_solar" : "solar";
    var batteryKey = state.chartMode === "forecast" ? "forecast_battery" : "battery";
    var demand = numericArray(firstDefined(energy[demandKey], energy.demand), DEMO_DATA.energy.demand);
    var solar = numericArray(firstDefined(energy[solarKey], energy.solar), DEMO_DATA.energy.solar);
    var battery = numericArray(firstDefined(energy[batteryKey], energy.battery), DEMO_DATA.energy.battery);
    var upper = numericArray(firstDefined(energy.upper, energy.confidence_upper), DEMO_DATA.energy.upper);
    var lower = numericArray(firstDefined(energy.lower, energy.confidence_lower), DEMO_DATA.energy.lower);
    var length = Math.max(labels.length, demand.length, solar.length, battery.length);
    return {
      labels: padArray(labels, length, "—"),
      demand: padArray(demand, length, 0),
      solar: padArray(solar, length, 0),
      battery: padArray(battery, length, 0),
      upper: padArray(upper, length, 0),
      lower: padArray(lower, length, 0),
      currentIndex: Math.min(length - 1, Math.max(0, numberValue(energy.current_index, 7))),
      confidence: numberValue(energy.confidence, numberValue(state.data.monitoring && state.data.monitoring.confidence, 94))
    };
  }

  function numericArray(value, fallback) {
    if (!Array.isArray(value)) return fallback.slice();
    return value.map(function (item, index) { return numberValue(item, fallback[index] === undefined ? 0 : fallback[index]); });
  }

  function padArray(array, length, fill) {
    var result = array.slice(0, length);
    while (result.length < length) result.push(result.length ? result[result.length - 1] : fill);
    return result;
  }

  function svgElement(tag, attrs) {
    var element = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (key) { element.setAttribute(key, attrs[key]); });
    return element;
  }

  function pathFor(values, x, y) {
    return values.map(function (value, index) {
      return (index === 0 ? "M" : "L") + " " + x(index).toFixed(2) + " " + y(value).toFixed(2);
    }).join(" ");
  }

  function areaFor(values, x, y, bottom) {
    if (!values.length) return "";
    var top = pathFor(values, x, y);
    return top + " L " + x(values.length - 1).toFixed(2) + " " + bottom.toFixed(2) + " L " + x(0).toFixed(2) + " " + bottom.toFixed(2) + " Z";
  }

  function renderChart() {
    var svg = $("#energyChart");
    if (!svg) return;
    var groups = {
      grid: $("#chartGrid"),
      band: $("#chartBand"),
      areas: $("#chartAreas"),
      lines: $("#chartLines"),
      markers: $("#chartMarkers"),
      labels: $("#chartLabels")
    };
    Object.keys(groups).forEach(function (key) { if (groups[key]) groups[key].innerHTML = ""; });

    var chart = getEnergyArrays();
    var width = 960;
    var height = 320;
    var margin = { left: 43, right: 12, top: 15, bottom: 34 };
    var innerWidth = width - margin.left - margin.right;
    var innerHeight = height - margin.top - margin.bottom;
    var maxValue = Math.max.apply(null, chart.upper.concat(chart.demand).concat(chart.solar).concat(chart.battery.map(function (v) { return Math.abs(v); }))) || 4;
    maxValue = Math.max(3.2, Math.ceil(maxValue * 1.12 * 10) / 10);
    var minValue = -0.75;
    var x = function (index) { return margin.left + (chart.labels.length <= 1 ? 0 : index / (chart.labels.length - 1)) * innerWidth; };
    var y = function (value) { return margin.top + (maxValue - value) / (maxValue - minValue) * innerHeight; };
    var bottom = y(minValue);

    var defs = svgElement("defs", {});
    var demandGradient = svgElement("linearGradient", { id: "demandGradient", x1: "0", x2: "0", y1: "0", y2: "1" });
    demandGradient.appendChild(svgElement("stop", { offset: "0%", "stop-color": "#45e1c3", "stop-opacity": "0.36" }));
    demandGradient.appendChild(svgElement("stop", { offset: "100%", "stop-color": "#45e1c3", "stop-opacity": "0" }));
    var solarGradient = svgElement("linearGradient", { id: "solarGradient", x1: "0", x2: "0", y1: "0", y2: "1" });
    solarGradient.appendChild(svgElement("stop", { offset: "0%", "stop-color": "#b7e77b", "stop-opacity": "0.28" }));
    solarGradient.appendChild(svgElement("stop", { offset: "100%", "stop-color": "#b7e77b", "stop-opacity": "0" }));
    defs.appendChild(demandGradient);
    defs.appendChild(solarGradient);
    svg.insertBefore(defs, svg.firstChild);

    var ticks = 4;
    for (var tick = 0; tick <= ticks; tick += 1) {
      var value = maxValue - ((maxValue - minValue) / ticks) * tick;
      var yPos = y(value);
      groups.grid.appendChild(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: yPos, y2: yPos, class: "chart-grid-line" }));
      var label = svgElement("text", { x: 0, y: yPos + 3, class: "chart-grid-label" });
      label.textContent = value.toFixed(1) + " MW";
      groups.grid.appendChild(label);
    }

    var zeroLine = y(0);
    groups.grid.appendChild(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: zeroLine, y2: zeroLine, class: "chart-grid-line" }));

    var xStep = chart.labels.length > 9 ? 2 : 1;
    chart.labels.forEach(function (label, index) {
      if (index % xStep !== 0 && index !== chart.labels.length - 1) return;
      var xPos = x(index);
      groups.grid.appendChild(svgElement("line", { x1: xPos, x2: xPos, y1: margin.top, y2: bottom, class: "chart-grid-line", opacity: "0.45" }));
      var xLabel = svgElement("text", { x: xPos, y: height - 8, class: "chart-x-label", "text-anchor": index === 0 ? "start" : index === chart.labels.length - 1 ? "end" : "middle" });
      xLabel.textContent = String(label);
      groups.labels.appendChild(xLabel);
    });

    var bandValuesTop = chart.upper.length ? chart.upper : chart.demand.map(function (v) { return v + 0.15; });
    var bandValuesBottom = chart.lower.length ? chart.lower : chart.demand.map(function (v) { return v - 0.15; });
    var bandPath = pathFor(bandValuesTop, x, y) + " " + bandValuesBottom.slice().reverse().map(function (value, reverseIndex) {
      var originalIndex = bandValuesBottom.length - 1 - reverseIndex;
      return "L " + x(originalIndex).toFixed(2) + " " + y(value).toFixed(2);
    }).join(" ") + " Z";
    groups.band.appendChild(svgElement("path", { d: bandPath, class: "chart-band-path" }));

    groups.areas.appendChild(svgElement("path", { d: areaFor(chart.demand, x, y, bottom), class: "chart-area-demand" }));
    groups.areas.appendChild(svgElement("path", { d: areaFor(chart.solar, x, y, bottom), class: "chart-area-solar" }));
    groups.lines.appendChild(svgElement("path", { d: pathFor(chart.demand, x, y), class: "chart-line chart-line-demand" }));
    groups.lines.appendChild(svgElement("path", { d: pathFor(chart.solar, x, y), class: "chart-line chart-line-solar" }));
    groups.lines.appendChild(svgElement("path", { d: pathFor(chart.battery, x, y), class: "chart-line chart-line-battery" }));

    var currentX = x(chart.currentIndex);
    groups.markers.appendChild(svgElement("line", { x1: currentX, x2: currentX, y1: margin.top, y2: bottom, class: "chart-now-line" }));
    var nowRect = svgElement("rect", { x: currentX - 19, y: 1, width: 38, height: 16, rx: 5, class: "chart-now-pill" });
    groups.markers.appendChild(nowRect);
    var nowText = svgElement("text", { x: currentX, y: 12, class: "chart-now-text", "text-anchor": "middle" });
    nowText.textContent = "NOW";
    groups.markers.appendChild(nowText);

    ["demand", "solar"].forEach(function (series) {
      var values = chart[series];
      var current = values[chart.currentIndex];
      if (current === undefined) return;
      groups.markers.appendChild(svgElement("circle", { cx: currentX, cy: y(current), r: 4.2, class: "chart-marker chart-marker-" + series }));
    });

    var energy = state.data.energy || {};
    setText("peakImport", numberValue(firstDefined(energy.peak_import, energy.peakImport), 2.42).toFixed(2) + " MW");
    setText("peakImportTime", stringValue(firstDefined(energy.peak_import_time, energy.peakImportTime), "18:00") + " · " + stringValue(firstDefined(energy.peak_import_delta, energy.peakImportDelta), "−18% vs baseline"));
    setText("solarWindow", stringValue(firstDefined(energy.solar_window, energy.solarWindow), "10:00 — 16:00"));
    setText("solarWindowDetail", stringValue(firstDefined(energy.solar_window_detail, energy.solarWindowDetail), "1.18 MWh available to shift"));
    setText("nextDecision", stringValue(firstDefined(energy.next_decision, energy.nextDecision), "in 18 min"));
    setupChartPointer(svg, chart, x, innerWidth, margin.left);
  }

  function setupChartPointer(svg, chart, x, innerWidth, leftMargin) {
    var oldOverlay = svg.querySelector(".chart-pointer-overlay");
    if (oldOverlay) oldOverlay.remove();
    var overlay = svgElement("rect", { x: leftMargin, y: 0, width: innerWidth, height: 285, fill: "transparent", class: "chart-pointer-overlay" });
    overlay.style.cursor = "crosshair";
    svg.appendChild(overlay);
    var stage = $(".chart-stage");
    var line = $("#chartHoverLine");
    var tooltip = $("#chartTooltip");
    if (!stage || !line || !tooltip) return;
    overlay.addEventListener("mousemove", function (event) {
      var rect = svg.getBoundingClientRect();
      var ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
      var index = Math.round(ratio * (chart.labels.length - 1));
      var xRatio = (x(index) / 960) * 100;
      line.style.left = xRatio + "%";
      line.classList.remove("hidden");
      tooltip.innerHTML = "<strong>" + escapeHtml(chart.labels[index]) + "</strong>" +
        '<span>Demand <em>' + chart.demand[index].toFixed(2) + " MW</em></span>" +
        '<span>Solar <em>' + chart.solar[index].toFixed(2) + " MW</em></span>" +
        '<span>Battery <em>' + (chart.battery[index] >= 0 ? "+" : "") + chart.battery[index].toFixed(2) + " MW</em></span>";
      var left = Math.min(stage.clientWidth - 150, Math.max(5, event.clientX - rect.left - 55));
      tooltip.style.left = left + "px";
      tooltip.style.top = Math.max(5, event.clientY - rect.top - 84) + "px";
      tooltip.classList.remove("hidden");
    });
    overlay.addEventListener("mouseleave", function () {
      line.classList.add("hidden");
      tooltip.classList.add("hidden");
    });
  }

  function normalizeStatus(status) {
    var value = String(status || "charging").toLowerCase().replace(/[_\s-]+/g, "");
    if (value.indexOf("ready") >= 0 || value.indexOf("complete") >= 0) return "ready";
    if (value.indexOf("attention") >= 0 || value.indexOf("warning") >= 0 || value.indexOf("alert") >= 0) return "attention";
    if (value.indexOf("pause") >= 0 || value.indexOf("idle") >= 0) return "paused";
    return "charging";
  }

  function renderFleet() {
    var fleet = state.data.fleet || {};
    var vehicles = Array.isArray(fleet) ? fleet : (Array.isArray(fleet.vehicles) ? fleet.vehicles : []);
    var query = state.fleetSearch.trim().toLowerCase();
    var filtered = vehicles.filter(function (vehicle) {
      var status = normalizeStatus(firstDefined(vehicle.status, vehicle.state));
      var filterMatch = state.fleetFilter === "all" || state.fleetFilter === status;
      var searchMatch = !query || [vehicle.id, vehicle.model, vehicle.site, vehicle.status].join(" ").toLowerCase().indexOf(query) >= 0;
      return filterMatch && searchMatch;
    });
    var pageSize = 5;
    var pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    if (state.fleetPage >= pageCount) state.fleetPage = 0;
    var start = state.fleetPage * pageSize;
    var rows = filtered.slice(start, start + pageSize);
    var tbody = $("#fleetRows");
    if (tbody) {
      tbody.innerHTML = rows.length ? rows.map(function (vehicle) { return fleetRow(vehicle); }).join("") : '<tr><td colspan="7" class="empty-table">No vehicles match this view.</td></tr>';
    }
    setText("fleetTableSummary", "Showing " + (rows.length ? start + 1 : 0) + "–" + (start + rows.length) + " of " + filtered.length + " vehicles");
    var next = $("#fleetNextButton");
    if (next) next.disabled = pageCount <= 1;

    var counts = { all: vehicles.length, charging: 0, ready: 0, attention: 0 };
    vehicles.forEach(function (vehicle) { var status = normalizeStatus(firstDefined(vehicle.status, vehicle.state)); if (counts[status] !== undefined) counts[status] += 1; });
    setText("fleetAllCount", counts.all || numberValue(fleet.total, 24));
    setText("fleetChargingCount", counts.charging);
    setText("fleetReadyCount", counts.ready);
    setText("fleetAttentionCount", counts.attention);
    var navCount = $(".nav-link[data-view=\"fleet\"] .nav-count");
    if (navCount) navCount.textContent = String(numberValue(fleet.total, vehicles.length || 24));
  }

  function fleetRow(vehicle) {
    var status = normalizeStatus(firstDefined(vehicle.status, vehicle.state));
    var labels = { charging: "Charging", ready: "Ready", attention: "Attention", paused: "Paused" };
    var soc = numberValue(firstDefined(vehicle.soc, vehicle.state_of_charge, vehicle.battery_percent), 0);
    var target = numberValue(firstDefined(vehicle.target, vehicle.departure_target), 80);
    var low = soc < Math.max(35, target - 20);
    var id = stringValue(firstDefined(vehicle.id, vehicle.vehicle_id), "EV-—");
    var model = stringValue(firstDefined(vehicle.model, vehicle.make), "Electric van");
    var site = stringValue(firstDefined(vehicle.site, vehicle.location), "—");
    var eta = stringValue(firstDefined(vehicle.eta, vehicle.charge_eta), status === "ready" ? "Ready" : "—");
    var departure = stringValue(firstDefined(vehicle.departure, vehicle.departure_time), "—");
    var power = numberValue(firstDefined(vehicle.power, vehicle.power_kw), 0);
    var initial = escapeHtml(id.slice(-2));
    return "<tr>" +
      '<td><div class="vehicle-cell"><span class="vehicle-avatar">' + initial + "</span><span class=\"vehicle-copy\"><strong>" + escapeHtml(id) + "</strong><small>" + escapeHtml(model) + "</small></span></div></td>" +
      '<td class="site-cell">' + escapeHtml(site) + "</td>" +
      '<td class="soc-cell"><div class="soc-row"><strong>' + Math.round(soc) + "%</strong><span class=\"soc-track " + (low ? "low" : "") + '\"><span style="width:' + Math.max(0, Math.min(100, soc)) + '%"></span></span></div></td>' +
      '<td><span class="departure-time">' + escapeHtml(departure) + "<small>ETA " + escapeHtml(eta) + "</small></span></td>" +
      '<td class="power-cell">' + (power ? formatNumber(power) + " kW" : "—") + "</td>" +
      '<td><span class="status-pill status-' + status + '">' + labels[status] + "</span></td>" +
      '<td><button class="row-menu" type="button" data-vehicle-menu="' + escapeHtml(id) + '" aria-label="Open actions for ' + escapeHtml(id) + '" title="Vehicle actions">•••</button></td>' +
      "</tr>";
  }

  function renderAgents() {
    var agents = Array.isArray(state.data.agents) && state.data.agents.length ? state.data.agents : DEMO_DATA.agents;
    var timeline = $("#agentTimeline");
    if (!timeline) return;
    timeline.innerHTML = agents.slice(0, 5).map(function (agent) {
      var tone = stringValue(agent.tone, "violet");
      return '<div class="timeline-item"><span class="timeline-node ' + escapeHtml(tone) + '">' + escapeHtml(stringValue(agent.icon, "✦")) + '</span><div class="timeline-copy"><strong>' + escapeHtml(stringValue(agent.title, "Agent update")) + '</strong><p>' + escapeHtml(stringValue(agent.text, "Telemetry review completed.")) + '</p></div><span class="timeline-time">' + escapeHtml(stringValue(agent.time, "now")) + "</span></div>";
    }).join("");
  }

  function renderMonitoring() {
    var monitoring = state.data.monitoring || {};
    var freshness = numberValue(firstDefined(monitoring.freshness_seconds, monitoring.freshness), 12);
    var freshnessPercent = numberValue(firstDefined(monitoring.freshness_percent), Math.max(0, Math.min(100, 100 - freshness / 60 * 8)));
    var completeness = numberValue(firstDefined(monitoring.completeness, monitoring.telemetry_completeness), 99.2);
    var confidence = numberValue(firstDefined(monitoring.confidence, monitoring.forecast_confidence), 94);
    var drift = numberValue(firstDefined(monitoring.drift, monitoring.model_drift), 0.8);
    setText("monitoringOverall", stringValue(monitoring.overall, "Healthy"));
    setText("monitoringFreshness", Math.round(freshness) + " sec");
    setWidth("monitoringFreshnessBar", freshnessPercent);
    setText("monitoringCompleteness", completeness.toFixed(1) + "%");
    setWidth("monitoringCompletenessBar", completeness);
    setText("monitoringConfidence", Math.round(confidence) + "%");
    setWidth("monitoringConfidenceBar", confidence);
    setText("monitoringDrift", drift.toFixed(1) + "%");
    setWidth("monitoringDriftBar", Math.min(100, drift * 22));
    setText("modelVersion", stringValue(monitoring.model_version, "dispatch-forecast-v2.4"));
    setText("lastEvaluation", stringValue(monitoring.evaluated, "14 min ago"));
  }

  function renderAll() {
    renderDataSource();
    renderKpis();
    renderFlow();
    renderRecommendation();
    renderChart();
    renderFleet();
    renderAgents();
    renderMonitoring();
    setText("sideHealthTime", state.usingFallback ? "demo snapshot" : "12 sec ago");
  }

  function setLoading(isLoading) {
    var refresh = $("#refreshButton");
    if (refresh) {
      refresh.disabled = isLoading;
      refresh.classList.toggle("is-refreshing", isLoading);
    }
  }

  function loadDashboard(showResultToast) {
    setLoading(true);
    var dashboardRequest = apiRequest("/api/dashboard");
    var monitoringRequest = apiRequest("/api/monitoring");
    return Promise.allSettled([dashboardRequest, monitoringRequest]).then(function (results) {
      var dashboardResult = results[0];
      var monitoringResult = results[1];
      state.apiStatus.dashboard = dashboardResult.status === "fulfilled";
      state.apiStatus.monitoring = monitoringResult.status === "fulfilled";

      if (state.apiStatus.dashboard) {
        state.data = normalizePayload(dashboardResult.value);
        state.usingFallback = false;
      } else {
        state.data = clone(DEMO_DATA);
        state.usingFallback = true;
      }
      if (state.apiStatus.monitoring) {
        var monitoringPayload = monitoringResult.value;
        var monitoring = monitoringPayload && (monitoringPayload.monitoring || monitoringPayload.data || monitoringPayload);
        if (isObject(monitoring)) state.data.monitoring = merge(state.data.monitoring, monitoring);
      }
      state.lastSync = new Date();
      renderAll();
      if (showResultToast) {
        showToast(state.usingFallback ? "Showing seeded demo telemetry; service will be retried on refresh." : "Dashboard telemetry refreshed.", state.usingFallback ? "warning" : "success");
      }
      return state.data;
    }).catch(function () {
      state.data = clone(DEMO_DATA);
      state.usingFallback = true;
      state.lastSync = new Date();
      renderAll();
      if (showResultToast) showToast("The dashboard service is unavailable; demo telemetry is still live.", "warning");
      return state.data;
    }).finally(function () {
      setLoading(false);
    });
  }

  function openOptimizationModal() {
    var modal = $("#optimizationModal");
    if (!modal) return;
    state.previousFocus = document.activeElement;
    modal.classList.remove("hidden");
    document.body.classList.add("modal-open");
    var error = $("#modalError");
    if (error) { error.textContent = ""; error.classList.add("hidden"); }
    window.setTimeout(function () { var select = $("#optimizationScenario"); if (select) select.focus(); }, 30);
    updateSimulationPreview();
  }

  function closeOptimizationModal() {
    var modal = $("#optimizationModal");
    if (!modal) return;
    modal.classList.add("hidden");
    document.body.classList.remove("modal-open");
    if (state.previousFocus && typeof state.previousFocus.focus === "function") state.previousFocus.focus();
  }

  function updateSimulationPreview() {
    var scenario = $("#optimizationScenario");
    var horizon = $("#horizonRange");
    var reserve = $("#reserveRange");
    var horizonValue = numberValue(horizon && horizon.value, 8);
    var reserveValue = numberValue(reserve && reserve.value, 30);
    setText("horizonValue", horizonValue + (horizonValue === 1 ? " hour" : " hours"));
    setText("reserveValue", reserveValue + "%");
    var scenarioValue = scenario ? scenario.value : "solar_shift";
    var flexible = scenarioValue === "departure_ready" ? 6 : scenarioValue === "peak_shave" ? 12 : 9;
    var low = Math.max(18, 31 + (horizonValue - 8) * 1.2 - (reserveValue - 30) * 0.25);
    var high = low + (scenarioValue === "peak_shave" ? 22 : 14);
    setText("previewVehicles", flexible);
    setText("previewSavings", "$" + Math.round(low) + "–$" + Math.round(high));
  }

  function scenarioRecommendation(scenario, horizon, reserve) {
    var base = clone(DEMO_DATA.recommendation);
    if (scenario === "peak_shave") {
      base.title = "Stage 12 vehicles before the evening peak";
      base.summary = "Pause non-critical sessions before 17:30, then release stored energy across the 18:00 tariff boundary while keeping every route reserve intact.";
      base.savings = "$52.80";
      base.peak_reduction = "−610 kW";
      base.carbon = "104 kg";
      base.reasons = ["Peak tariff begins in " + Math.max(1, horizon - 3) + " hours", "Battery headroom is sufficient for a two-hour dispatch", "All priority routes remain above their reserve target"];
    } else if (scenario === "departure_ready") {
      base.title = "Protect the 06:10 departure commitment";
      base.summary = "Prioritize the South Loop route and re-sequence flexible sessions so the early departure clears its target without exceeding the site import policy.";
      base.savings = "$24.10";
      base.peak_reduction = "−180 kW";
      base.carbon = "48 kg";
      base.reasons = ["EV-091 is below its readiness target", "Two flexible sessions can move by 35 minutes", "Import remains below the protected 2.40 MW cap"];
    } else if (scenario === "price_signal") {
      base.title = "Follow the low-cost tariff signal";
      base.summary = "Move flexible charging into the next low-cost interval, then settle the fleet before the first route wave while preserving the configured reserve floor.";
      base.savings = "$46.70";
      base.peak_reduction = "−350 kW";
      base.carbon = "72 kg";
      base.reasons = ["Next low-cost interval lasts " + Math.min(4, horizon) + " hours", "9 sessions can shift without route impact", "Reserve floor remains protected at " + reserve + "%"];
    } else {
      base.reasons = ["9 vehicles have flexible departure windows", "PV forecast is above the 7-day median", "Reserve floor remains protected at " + reserve + "%"];
    }
    base.age = "simulation just now";
    base.confidence = Math.max(82, Math.min(98, 94 - Math.abs(reserve - 30) * 0.18));
    return base;
  }

  function addAgentEvent(title, text, tone, icon) {
    var current = Array.isArray(state.data.agents) ? state.data.agents : [];
    current.unshift({ time: "now", title: title, text: text, tone: tone || "violet", icon: icon || "✦" });
    state.data.agents = current.slice(0, 5);
    renderAgents();
  }

  function runOptimization(event) {
    if (event) event.preventDefault();
    if (state.optimizationRunning) return;
    state.optimizationRunning = true;
    var scenario = $("#optimizationScenario");
    var horizon = $("#horizonRange");
    var reserve = $("#reserveRange");
    var submit = $("#runOptimizationButton");
    var spinner = $("#optimizationSpinner");
    var label = $("#runOptimizationLabel");
    var error = $("#modalError");
    if (submit) submit.disabled = true;
    if (spinner) spinner.classList.remove("hidden");
    if (label) label.textContent = "Running safe simulation";
    if (error) error.classList.add("hidden");

    var body = {
      scenario: scenario ? scenario.value : "solar_shift",
      horizon_hours: numberValue(horizon && horizon.value, 8),
      reserve_soc: numberValue(reserve && reserve.value, 30),
      objectives: $$('input[name="objective"]:checked').map(function (input) { return input.value; }),
      vehicle_ids: (state.data.fleet.vehicles || []).map(function (vehicle) { return vehicle.id; })
    };

    var simulated = scenarioRecommendation(body.scenario, body.horizon_hours, body.reserve_soc);
    var request = apiRequest("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    request.then(function (payload) {
      var result = payload && (payload.recommendation || payload.result || payload.data || payload);
      if (isObject(result)) simulated = merge(simulated, result);
      state.data.recommendation = simulated;
      state.recommendationDismissed = false;
      renderRecommendation();
      addAgentEvent("Optimization simulation completed", "Reviewed " + body.objectives.length + " objectives across a " + body.horizon_hours + "-hour horizon.", "violet", "✦");
      closeOptimizationModal();
      showToast("Simulation ready for human review.", "success");
    }).catch(function () {
      state.data.recommendation = simulated;
      state.recommendationDismissed = false;
      renderRecommendation();
      addAgentEvent("Local what-if simulation completed", "Service unavailable; the seeded dispatch model produced a safe preview.", "orange", "◌");
      closeOptimizationModal();
      showToast("Service unavailable — showing a local safe simulation preview.", "warning");
    }).finally(function () {
      state.optimizationRunning = false;
      if (submit) submit.disabled = false;
      if (spinner) spinner.classList.add("hidden");
      if (label) label.textContent = "Run simulation";
    });
  }

  function submitFeedback() {
    if (!state.selectedFeedback) return;
    var button = $("#submitFeedbackButton");
    if (button) button.disabled = true;
    var comment = $("#feedbackComment");
    var body = {
      recommendation_id: stringValue(state.data.recommendation && state.data.recommendation.id, DEMO_DATA.recommendation.id),
      rating: state.selectedFeedback,
      comment: comment ? comment.value.trim() : "",
      source: "energy-command-center"
    };
    apiRequest("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).catch(function () { return null; }).finally(function () {
      var thanks = $("#feedbackThanks");
      if (thanks) thanks.classList.remove("hidden");
      if (comment) comment.value = "";
      $$(".feedback-button").forEach(function (feedbackButton) { feedbackButton.classList.remove("selected"); });
      state.selectedFeedback = null;
      showToast("Feedback added to the team review queue.", "success");
      window.setTimeout(function () { if (thanks) thanks.classList.add("hidden"); }, 6000);
    });
  }

  function navigate(view) {
    var map = {
      overview: "#overview",
      fleet: "#fleetSection",
      microgrid: "#microgridSection",
      agents: "#agentsSection",
      monitoring: "#monitoringSection",
      guardrails: "#guardrailsSection",
      reports: null
    };
    $$(".nav-link[data-view]").forEach(function (link) {
      var active = link.getAttribute("data-view") === view;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    if (map[view]) {
      var target = $(map[view]);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (view === "reports") {
      showToast("Reports are available after the next evaluation window.", "warning");
    }
    document.body.classList.remove("sidebar-open");
  }

  function bindEvents() {
    $$(".nav-link[data-view]").forEach(function (link) {
      link.addEventListener("click", function () { navigate(link.getAttribute("data-view")); });
    });

    var openButtons = [$("#openOptimizationButton"), $("#reviewOptimizationButton")];
    openButtons.forEach(function (button) { if (button) button.addEventListener("click", openOptimizationModal); });
    var closeButton = $("#closeOptimizationButton");
    var cancelButton = $("#cancelOptimizationButton");
    if (closeButton) closeButton.addEventListener("click", closeOptimizationModal);
    if (cancelButton) cancelButton.addEventListener("click", closeOptimizationModal);
    var modal = $("#optimizationModal");
    if (modal) modal.addEventListener("click", function (event) { if (event.target === modal) closeOptimizationModal(); });
    var form = $("#optimizationForm");
    if (form) form.addEventListener("submit", runOptimization);
    [$("#horizonRange"), $("#reserveRange"), $("#optimizationScenario")].forEach(function (input) { if (input) input.addEventListener("input", updateSimulationPreview); });

    $$(".chart-tab[data-chart-mode]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        state.chartMode = tab.getAttribute("data-chart-mode");
        $$(".chart-tab[data-chart-mode]").forEach(function (other) {
          var active = other === tab;
          other.classList.toggle("active", active);
          other.setAttribute("aria-selected", active ? "true" : "false");
        });
        renderChart();
      });
    });

    $$(".fleet-tab[data-fleet-filter]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        state.fleetFilter = tab.getAttribute("data-fleet-filter");
        state.fleetPage = 0;
        $$(".fleet-tab[data-fleet-filter]").forEach(function (other) {
          var active = other === tab;
          other.classList.toggle("active", active);
          other.setAttribute("aria-selected", active ? "true" : "false");
        });
        renderFleet();
      });
    });

    var search = $("#fleetSearch");
    if (search) search.addEventListener("input", function () { state.fleetSearch = search.value; state.fleetPage = 0; renderFleet(); });
    var next = $("#fleetNextButton");
    if (next) next.addEventListener("click", function () { state.fleetPage += 1; renderFleet(); });
    [$("#viewFleetButton"), $("#viewActivityButton")].forEach(function (button) {
      if (button) button.addEventListener("click", function () { navigate(button.id === "viewFleetButton" ? "fleet" : "agents"); });
    });

    $$("[data-feedback-rating]").forEach(function (button) {
      button.addEventListener("click", function () {
        state.selectedFeedback = button.getAttribute("data-feedback-rating");
        $$("[data-feedback-rating]").forEach(function (other) { other.classList.toggle("selected", other === button); });
        var submit = $("#submitFeedbackButton");
        if (submit) submit.disabled = false;
      });
    });
    var feedbackSubmit = $("#submitFeedbackButton");
    if (feedbackSubmit) feedbackSubmit.addEventListener("click", submitFeedback);

    var refresh = $("#refreshButton");
    if (refresh) refresh.addEventListener("click", function () { loadDashboard(true); });
    var retry = $("#retryApiButton");
    if (retry) retry.addEventListener("click", function () { state.bannerDismissed = false; loadDashboard(true); });
    var dismiss = $("#dismissBannerButton");
    if (dismiss) dismiss.addEventListener("click", function () { state.bannerDismissed = true; renderDataSource(); });
    var mobileButton = $("#mobileMenuButton");
    if (mobileButton) mobileButton.addEventListener("click", function () { document.body.classList.toggle("sidebar-open"); });
    var backdrop = $("#mobileBackdrop");
    if (backdrop) backdrop.addEventListener("click", function () { document.body.classList.remove("sidebar-open"); });
    var dismissRecommendation = $("#dismissRecommendationButton");
    if (dismissRecommendation) dismissRecommendation.addEventListener("click", function () {
      state.recommendationDismissed = true;
      renderRecommendation();
      showToast("Recommendation snoozed for this operating window.", "warning");
    });

    $$("#privacyLink, #statusLink").forEach(function (link) {
      link.addEventListener("click", function (event) { event.preventDefault(); showToast(link.id === "statusLink" ? "All systems nominal · telemetry online." : "Demo workspace data stays in this browser.", "success"); });
    });

    document.addEventListener("click", function (event) {
      var menu = event.target.closest && event.target.closest("[data-vehicle-menu]");
      if (menu) showToast("Vehicle actions for " + menu.getAttribute("data-vehicle-menu") + " are review-only in this demo.", "warning");
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        if (modal && !modal.classList.contains("hidden")) closeOptimizationModal();
        else document.body.classList.remove("sidebar-open");
      }
    });

    var exportButton = $("#exportButton");
    if (exportButton) exportButton.addEventListener("click", exportSnapshot);
  }

  function exportSnapshot() {
    var snapshot = {
      exported_at: new Date().toISOString(),
      source: state.usingFallback ? "seeded-demo" : "api",
      workspace: "Metro Fleet",
      kpis: state.data.kpis,
      recommendation: state.data.recommendation,
      monitoring: state.data.monitoring
    };
    try {
      var blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "nexgrid-energy-snapshot.json";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(function () { URL.revokeObjectURL(url); }, 300);
      showToast("Snapshot exported as JSON.", "success");
    } catch (error) {
      showToast("Export is unavailable in this browser.", "error");
    }
  }

  function start() {
    bindEvents();
    renderAll();
    loadDashboard(false);
    window.setInterval(function () {
      if (document.visibilityState !== "hidden" && !state.optimizationRunning) loadDashboard(false);
    }, REFRESH_INTERVAL_MS);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
