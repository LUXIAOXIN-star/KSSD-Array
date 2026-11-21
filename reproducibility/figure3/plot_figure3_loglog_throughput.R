#!/usr/bin/env Rscript
# Figure 3: absolute measured throughput on log2/log2 axes.
# Reads only the original summary CSV, with no one-thread normalization.
script_arg <- grep("^--file=", commandArgs(trailingOnly=FALSE), value=TRUE)
if (length(script_arg) != 1L) stop("Run this file with Rscript")
script_path <- normalizePath(sub("^--file=", "", script_arg), mustWork=TRUE)
project_root <- normalizePath(file.path(dirname(script_path), "..", ".."), mustWork=TRUE)
args <- commandArgs(trailingOnly=TRUE)
if ("--help" %in% args) {
  cat("Usage: Rscript plot_figure3_loglog_throughput.R --out NEW_DIR [--data-dir FIGURE3_DATA_DIR]\n")
  quit(status=0)
}
option <- function(name, default=NULL) {
  pos <- match(name, args)
  if (is.na(pos)) return(default)
  if (pos == length(args)) stop("Missing value after ", name)
  args[[pos+1L]]
}
data_dir <- normalizePath(option("--data-dir", file.path(project_root, "benchmark_results", "figure3_multithread")), mustWork=TRUE)
out_value <- option("--out")
if (is.null(out_value)) stop("Specify --out with a new output directory")
if (file.exists(out_value) || dir.exists(out_value)) stop("Output already exists")
dir.create(out_value, recursive=TRUE)
outdir <- normalizePath(out_value, mustWork=TRUE)
Sys.setenv(XDG_CACHE_HOME=file.path(tempdir(), "font-cache"))
dir.create(Sys.getenv("XDG_CACHE_HOME"), recursive=TRUE, showWarnings=FALSE)
suppressPackageStartupMessages(library(ggplot2))
if (!capabilities("png") || !capabilities("cairo")) stop("Existing R needs Cairo PNG/PDF support")

datasets <- c("Synthetic_300_Mb", "GRCh38.p14_chr1")
methods <- c("KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "wyhash")
threads <- c(1L, 2L, 4L, 8L, 16L)
windows <- c(10L, 20L, 50L)
key_columns <- c("dataset", "k", "w", "threads", "method")
key <- function(d) do.call(paste, c(d[key_columns], sep="\r"))
source_path <- file.path(data_dir, "figure3_summary.csv")
mt <- read.csv(source_path, stringsAsFactors=FALSE, check.names=FALSE)
required <- c(key_columns, "n", "throughput_mwindows_s_mean", "throughput_mwindows_s_sd")
if (length(setdiff(required, names(mt)))) stop("Missing required summary columns")
expected <- expand.grid(dataset=datasets, k=21L, w=windows, threads=threads,
                        method=methods, stringsAsFactors=FALSE)
if (nrow(mt) != 150L || anyDuplicated(key(mt)) || !setequal(key(mt), key(expected))) {
  stop("Expected exactly 150 unique conditions, without missing or extra observations")
}
if (!is.numeric(mt$threads) || any(mt$n != 5L)) stop("Expected numeric threads and n=5")
if (any(!is.finite(mt$throughput_mwindows_s_mean)) ||
    any(!is.finite(mt$throughput_mwindows_s_sd)) ||
    any(mt$throughput_mwindows_s_mean <= 0) || any(mt$throughput_mwindows_s_sd < 0)) {
  stop("Mean and sample SD must be finite, with mean>0 and SD>=0")
}

# Error-bar endpoints are calculated in original M windows/s, before log transforms.
mt$lower <- mt$throughput_mwindows_s_mean - mt$throughput_mwindows_s_sd
mt$upper <- mt$throughput_mwindows_s_mean + mt$throughput_mwindows_s_sd
if (any(mt$lower <= 0)) stop("A mean-SD endpoint is not positive; do not clip it for a log axis")
y_powers <- seq.int(floor(log2(min(mt$lower))), ceiling(log2(max(mt$upper))))
y_breaks <- 2^y_powers
y_limits <- range(y_breaks)
if (any(mt$lower < y_limits[1L] | mt$upper > y_limits[2L])) stop("Y range would hide an error bar")

mt$dataset <- factor(mt$dataset, levels=datasets)
mt$method <- factor(mt$method, levels=methods)
parameter_labels <- paste0("k=21, w=", windows)
mt$parameter <- factor(paste0("k=21, w=", mt$w), levels=parameter_labels)
mt <- mt[order(mt$dataset, mt$parameter, mt$method, mt$threads), , drop=FALSE]

# Preserve the colours, marker shapes and method line types of the original figure.
colours <- setNames(c("#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"), methods)
line_types <- setNames(c("solid", "dashed", "dotdash", "dashed", "dotted"), methods)
shapes <- setNames(c(16, 15, 17, 18, 25), methods)
p <- ggplot(mt, aes(x=threads, y=throughput_mwindows_s_mean, colour=method, fill=method,
                    shape=method, linetype=method, group=method)) +
  geom_errorbar(aes(ymin=lower, ymax=upper), width=0.16, linewidth=0.30,
                linetype="solid", alpha=0.90, show.legend=FALSE) +
  geom_line(data=subset(mt, method != "KSSD-Array"), linewidth=0.58, alpha=0.90) +
  geom_point(data=subset(mt, method != "KSSD-Array"), size=1.25, stroke=0.22, alpha=0.95) +
  geom_line(data=subset(mt, method == "KSSD-Array"), linewidth=0.95, alpha=0.98) +
  geom_point(data=subset(mt, method == "KSSD-Array"), size=1.85, stroke=0.22, alpha=0.98) +
  facet_grid(dataset ~ parameter, scales="fixed") +
  scale_x_continuous(trans="log2", breaks=threads, labels=as.character(threads),
                     minor_breaks=NULL, expand=expansion(mult=c(0.055, 0.055))) +
  scale_y_continuous(trans="log2", breaks=y_breaks,
                     labels=format(y_breaks, trim=TRUE, scientific=FALSE),
                     limits=y_limits, minor_breaks=NULL,
                     expand=expansion(mult=c(0.02, 0.025))) +
  scale_colour_manual(name="Method", values=colours, breaks=methods, drop=FALSE) +
  scale_fill_manual(values=colours, breaks=methods) +
  scale_shape_manual(values=shapes, breaks=methods) +
  scale_linetype_manual(values=line_types, breaks=methods) +
  guides(colour=guide_legend(ncol=1, byrow=TRUE,
           override.aes=list(shape=unname(shapes), linetype=unname(line_types),
                             fill=unname(colours), alpha=1,
                             linewidth=c(0.92, rep(0.62, 4)), size=2.4)),
         fill="none", shape="none", linetype="none") +
  theme_classic(base_size=9, base_family="sans") +
  theme(axis.title=element_text(colour="#222222", size=10),
        axis.text=element_text(colour="#303030", size=9),
        axis.line=element_line(colour="#333333", linewidth=0.35),
        axis.ticks=element_line(colour="#333333", linewidth=0.30),
        legend.position="right", legend.direction="vertical", legend.justification="center",
        legend.title=element_text(size=9, colour="#222222"),
        legend.text=element_text(size=9, colour="#222222"),
        legend.key.width=grid::unit(1.5, "lines"),
        legend.key.height=grid::unit(0.9, "lines"),
        legend.box.margin=margin(0, 0, 0, 5),
        panel.grid.major.y=element_line(colour="#E6E6E6", linewidth=0.28),
        panel.grid.major.x=element_blank(), panel.grid.minor=element_blank(),
        strip.background=element_rect(fill="#F2F2F2", colour="#BDBDBD", linewidth=0.35),
        strip.text=element_text(colour="#222222", size=9, face="bold"),
        plot.margin=margin(7, 9, 5, 7)) +
  labs(x="Threads", y="Throughput (M windows/s)")

# Verify the actual ggplot layers against the source values and raw-unit endpoints.
built <- ggplot_build(p)
points <- rbind(built$data[[3L]], built$data[[5L]])
bars <- built$data[[1L]]
expected_values <- data.frame(
  PANEL=(as.integer(mt$dataset) - 1L) * length(windows) + as.integer(mt$parameter),
  colour=unname(colours[as.character(mt$method)]), x=log2(mt$threads),
  y=log2(mt$throughput_mwindows_s_mean), ymin=log2(mt$lower), ymax=log2(mt$upper))
# ggplot's group IDs are local to each layer; the preserved colours identify
# methods consistently across the separate KSSD and baseline point layers.
sort_values <- function(d) d[order(as.integer(d$PANEL), d$colour, d$x), , drop=FALSE]
expected_values <- sort_values(expected_values)
points <- sort_values(points)
bars <- sort_values(bars)
if (nrow(points) != 150L || nrow(bars) != 150L || length(unique(points$PANEL)) != 6L) {
  stop("The plot must retain all 150 points and error bars in six panels")
}
if (!identical(as.character(points$colour), expected_values$colour) ||
    !identical(as.character(bars$colour), expected_values$colour)) {
  stop("Plotted method identities differ from the source")
}
for (column in c("PANEL", "x", "y")) {
  if (any(!is.finite(as.numeric(points[[column]]))) ||
      max(abs(as.numeric(points[[column]]) - expected_values[[column]])) > 1e-12) {
    stop("Plotted points differ from source values: ", column)
  }
}
for (column in c("PANEL", "x", "ymin", "ymax")) {
  if (any(!is.finite(as.numeric(bars[[column]]))) ||
      max(abs(as.numeric(bars[[column]]) - expected_values[[column]])) > 1e-12) {
    stop("Plotted error bars differ from mean +/- SD: ", column)
  }
}
if (length(built$layout$panel_params) != 6L ||
    any(vapply(built$layout$panel_params, function(panel) {
      !identical(panel$y.range, built$layout$panel_params[[1L]]$y.range)
    }, logical(1L)))) stop("All panels must share the same Y range")

png_path <- file.path(outdir, "Figure3_loglog_throughput.png")
pdf_path <- file.path(outdir, "Figure3_loglog_throughput.pdf")
ggsave(png_path, p, device="png", type="cairo", width=10, height=5.1,
       units="in", dpi=610, bg="white")
ggsave(pdf_path, p, device=grDevices::cairo_pdf, width=10, height=5.1,
       units="in", bg="white")
svg_path <- file.path(outdir, "Figure3_loglog_throughput.svg")
ggsave(svg_path, p, device=grDevices::svg, width=10, height=5.1, units="in", bg="white")
caption <- paste(
  "Figure 3. Absolute multithread throughput of KSSD-Array, XXH3, XXH64,",
  "MurmurHash3, and wyhash on Synthetic_300_Mb and GRCh38.p14_chr1, with k=21",
  "and w=10, 20, or 50. Both axes use log2 coordinates; tick labels show actual",
  "thread counts and throughput in millions of windows per second (M windows/s).",
  "Points are the mean throughput from five measurements per condition, and",
  "error bars indicate the mean plus or minus one sample standard deviation.",
  "Error-bar endpoints are calculated in the original throughput units before",
  "the axis transformation. Ideally, throughput is proportional to the thread",
  "count, giving a straight line with slope 1 on these log-log axes; no ideal",
  "reference lines are overlaid. These are the original Figure 3 measurements:",
  "timing starts from pre-encoded k-mers and includes scoring and minimizer-window",
  "selection, with one result per window and no adjacent-window deduplication.",
  "FASTA parsing, DNA encoding, context initialization, parity checking, and",
  "wyhash-secret preparation are outside the timed methods. The original Figure 3",
  "driver used GCC 9.4.0 with -O3 -march=native -std=c11 -fopenmp; complete",
  "compilation and linkage records are retained in build_manifest.txt.",
  "The original protocol is documented in FIGURE3_FINAL_REPORT.md."
)
caption_path <- file.path(outdir, "Figure3_loglog_throughput_caption.txt")
writeLines(caption, caption_path, useBytes=TRUE)
cat("PASS: 150 source means and 150 mean+/-sample-SD error bars verified in six panels.\n")
cat("Every condition retains n=5; 30 method curves each have five thread points.\n")
cat(sprintf("Raw-unit error-bar range: %.15g to %.15g M windows/s.\n", min(mt$lower), max(mt$upper)))
cat(sprintf("Common Y limits: %.15g to %.15g; both axes use log2; no reference lines.\n", y_limits[1], y_limits[2]))
cat("PNG: 610 dpi, 6100 x 3111 pixels; PDF: Cairo vector text/lines.\n")
cat(paste(c(png_path, pdf_path, svg_path, caption_path), collapse="\n"), "\n")
