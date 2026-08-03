suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly=TRUE)
option_value <- function(name, default) {
  index <- match(name, args)
  if (is.na(index)) return(default)
  if (index == length(args)) stop(sprintf("Missing value after %s", name))
  args[[index + 1L]]
}
pairwise_path <- option_value("--pairwise", "benchmark_pairwise_speedups.csv")
by_k_path <- option_value("--by-k", "benchmark_summary_by_k.csv")
across_path <- option_value("--across-k", "benchmark_summary_across_k.csv")
outdir <- option_value("--output-dir", ".")

# Copied verbatim from the exact historical Figure 2/3 generator.
theme_kssd <- function(base_size=9) {
  theme_classic(base_size=base_size, base_family="sans") +
    theme(
      axis.title=element_text(color="#222222", size=base_size + 1),
      axis.text=element_text(color="#303030", size=base_size),
      axis.line=element_line(color="#333333", linewidth=0.35),
      axis.ticks=element_line(color="#333333", linewidth=0.30),
      legend.position="right",
      legend.direction="vertical",
      legend.justification="center",
      legend.title=element_text(size=base_size, color="#222222"),
      legend.text=element_text(size=base_size, color="#222222"),
      legend.key.width=unit(1.25, "lines"),
      legend.key.height=unit(0.82, "lines"),
      legend.box.margin=margin(0, 0, 0, 5),
      panel.grid.major.y=element_line(color="#E6E6E6", linewidth=0.28),
      panel.grid.major.x=element_blank(),
      panel.grid.minor=element_blank(),
      strip.background=element_rect(fill="#F2F2F2", color="#BDBDBD", linewidth=0.35),
      strip.text=element_text(color="#222222", size=base_size, face="bold"),
      plot.margin=margin(7, 7, 5, 7)
    )
}

pairwise <- read.csv(pairwise_path, stringsAsFactors=FALSE, check.names=FALSE)
by_k <- read.csv(by_k_path, stringsAsFactors=FALSE, check.names=FALSE)
across <- read.csv(across_path, stringsAsFactors=FALSE, check.names=FALSE)
if (nrow(pairwise) != 290L || nrow(by_k) != 116L || nrow(across) != 2L) {
  stop("Unexpected matched-workload accepted-table row count")
}
if (!all(pairwise$k == pairwise$w) || !all(by_k$k == by_k$w)) stop("Matched workload must satisfy k=w")

groups <- split(pairwise$kssd_over_nthash_speedup, paste(pairwise$dataset, pairwise$k, sep="\r"))
plot_data <- data.frame(
  key=names(groups),
  paired_speedup_median=vapply(groups, median, numeric(1)),
  pair_count=vapply(groups, length, integer(1)),
  stringsAsFactors=FALSE
)
parts <- strsplit(plot_data$key, "\r", fixed=TRUE)
plot_data$dataset <- vapply(parts, `[`, character(1), 1L)
plot_data$k <- as.integer(vapply(parts, `[`, character(1), 2L))
if (nrow(plot_data) != 58L || !all(plot_data$pair_count == 5L)) stop("Expected 58 five-pair points")

dataset_levels <- c("Synthetic_300M", "Human_GRCh38")
dataset_labels <- c("Synthetic_300M"="Synthetic 300 Mb", "Human_GRCh38"="GRCh38.p14 chr1")
plot_data$dataset_label <- factor(dataset_labels[plot_data$dataset], levels=dataset_labels[dataset_levels])
plot_data <- plot_data[order(plot_data$dataset_label, plot_data$k), ]

for (i in seq_len(nrow(across))) {
  values <- plot_data$paired_speedup_median[plot_data$dataset == across$dataset[i]]
  if (!isTRUE(all.equal(median(values), across$median_per_k_speedup[i], tolerance=1e-12))) {
    stop("Across-k median validation failed")
  }
  if (!isTRUE(all.equal(exp(mean(log(values))), across$geometric_mean_per_k_speedup[i], tolerance=1e-12))) {
    stop("Across-k geometric-mean validation failed")
  }
}

p <- ggplot(
  plot_data,
  aes(x=k, y=paired_speedup_median, shape=dataset_label,
      linetype=dataset_label, color=dataset_label, group=dataset_label)
) +
  geom_hline(yintercept=1, color="#6F6F6F", linewidth=0.28, linetype="dashed") +
  geom_line(linewidth=0.92, alpha=0.98) +
  geom_point(size=1.85, stroke=0.25, alpha=0.98) +
  scale_x_continuous(breaks=seq(4, 32, 4)) +
  scale_color_manual(name="Dataset", values=c("#1F77B4", "#E69F00")) +
  scale_shape_manual(name="Dataset", values=c(16, 18)) +
  scale_linetype_manual(name="Dataset", values=c("solid", "dashed")) +
  theme_kssd(9) +
  labs(x="Matched k-mer and window length (k = w)",
       y="Paired throughput ratio (KSSD-Array / ntHash)")

dir.create(outdir, recursive=TRUE, showWarnings=FALSE)
ggsave(file.path(outdir, "Table4_matched_speedup_vs_k_exact_manuscript_theme.png"),
       p, width=10.0, height=5.1, dpi=300, bg="white")
ggsave(file.path(outdir, "Table4_matched_speedup_vs_k_exact_manuscript_theme.pdf"),
       p, width=10.0, height=5.1, bg="white")
