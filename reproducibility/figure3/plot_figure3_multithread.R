#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly=TRUE)
value_after <- function(flag) {
  index <- match(flag, args)
  if (is.na(index) || index == length(args)) {
    stop(paste("missing required argument", flag))
  }
  args[[index + 1]]
}

summary_path <- value_after("--summary")
output_dir <- value_after("--output-dir")
dir.create(output_dir, recursive=TRUE, showWarnings=FALSE)

expected_methods <- c("KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "Wyhash")
method_colors <- c(
  "KSSD-Array"="#1F77B4",
  "XXH3"="#FF7F0E",
  "XXH64"="#2CA02C",
  "MurmurHash3"="#D62728",
  "Wyhash"="#9467BD"
)
method_linetypes <- c(
  "KSSD-Array"="solid",
  "XXH3"="dashed",
  "XXH64"="dotdash",
  "MurmurHash3"="longdash",
  "Wyhash"="dotted"
)
method_shapes <- c(
  "KSSD-Array"=16,
  "XXH3"=15,
  "XXH64"=17,
  "MurmurHash3"=18,
  "Wyhash"=25
)

summary <- read.csv(summary_path, stringsAsFactors=FALSE, check.names=FALSE)
required_columns <- c(
  "dataset", "k", "w", "threads", "method",
  "throughput_mwindows_s_mean"
)
if (!all(required_columns %in% names(summary))) {
  stop("summary CSV does not have the required Figure 3 columns")
}
if (!setequal(unique(summary$method), expected_methods)) {
  stop("summary CSV must contain exactly the five Figure 3 methods")
}
if (nrow(summary) == 0) {
  stop("summary CSV has no rows")
}

summary$method <- factor(summary$method, levels=expected_methods)
summary$threads <- as.numeric(summary$threads)
summary$throughput_mwindows_s_mean <- as.numeric(
  summary$throughput_mwindows_s_mean)
summary$w_label <- factor(
  paste0("k = ", summary$k, ", w = ", summary$w),
  levels=unique(paste0("k = ", summary$k, ", w = ", summary$w))
)
summary$dataset_label <- factor(summary$dataset, levels=unique(summary$dataset))
thread_breaks <- sort(unique(summary$threads))

plot <- ggplot(
  summary,
  aes(
    x=threads,
    y=throughput_mwindows_s_mean,
    color=method,
    fill=method,
    shape=method,
    linetype=method,
    group=method
  )
) +
  geom_line(
    data=subset(summary, method != "KSSD-Array"),
    linewidth=0.58,
    alpha=0.90
  ) +
  geom_point(
    data=subset(summary, method != "KSSD-Array"),
    size=1.35,
    stroke=0.22,
    alpha=0.95
  ) +
  geom_line(
    data=subset(summary, method == "KSSD-Array"),
    linewidth=0.95,
    alpha=0.98
  ) +
  geom_point(
    data=subset(summary, method == "KSSD-Array"),
    size=1.90,
    stroke=0.22,
    alpha=0.98
  ) +
  facet_grid(dataset_label ~ w_label, scales="free_y") +
  scale_x_continuous(trans="log2", breaks=thread_breaks) +
  scale_color_manual(name="Method", values=method_colors, breaks=expected_methods) +
  scale_fill_manual(name="Method", values=method_colors, breaks=expected_methods) +
  scale_shape_manual(name="Method", values=method_shapes, breaks=expected_methods) +
  scale_linetype_manual(
    name="Method", values=method_linetypes, breaks=expected_methods) +
  guides(fill="none", shape="none", linetype="none") +
  theme_classic(base_size=9, base_family="sans") +
  theme(
    axis.title=element_text(color="#222222", size=10),
    axis.text=element_text(color="#303030", size=9),
    axis.line=element_line(color="#333333", linewidth=0.35),
    axis.ticks=element_line(color="#333333", linewidth=0.30),
    legend.position="right",
    legend.direction="vertical",
    panel.grid.major.y=element_line(color="#E6E6E6", linewidth=0.28),
    panel.grid.major.x=element_blank(),
    panel.grid.minor=element_blank(),
    strip.background=element_rect(
      fill="#F2F2F2", color="#BDBDBD", linewidth=0.35),
    strip.text=element_text(color="#222222", size=9, face="bold")
  ) +
  labs(x="Threads", y="Throughput (M windows/s)")

png_path <- file.path(output_dir, "figure3_multithread_k21.png")
pdf_path <- file.path(output_dir, "figure3_multithread_k21.pdf")
ggsave(png_path, plot, width=10.0, height=5.1, dpi=300, bg="white")
ggsave(pdf_path, plot, width=10.0, height=5.1, bg="white")

message("Wrote ", png_path)
message("Wrote ", pdf_path)
