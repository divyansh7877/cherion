import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart, ScatterChart, GraphChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption, ECharts } from "echarts/core";

// Tree-shaken registration: only the chart types and components we actually use.
echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  GraphChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  CanvasRenderer,
]);

export interface EChartClickInfo {
  dataIndex: number;
  seriesIndex: number;
  dataType?: string; // 'node' | 'edge' for graph series
  name: string;
  data: unknown;
}

interface Props {
  option: EChartsCoreOption;
  height?: number;
  onDatumClick?: (info: EChartClickInfo) => void;
}

/** Thin React wrapper around ECharts: handles init, resize, dispose, and clicks. */
export default function EChart({ option, height = 380, onDatumClick }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setOption(option, true);
    chart.off("click");
    if (onDatumClick) {
      chart.on("click", (params: unknown) => {
        const p = params as EChartClickInfo;
        onDatumClick({
          dataIndex: p.dataIndex,
          seriesIndex: p.seriesIndex,
          dataType: p.dataType,
          name: p.name,
          data: p.data,
        });
      });
    }
  }, [option, onDatumClick]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
