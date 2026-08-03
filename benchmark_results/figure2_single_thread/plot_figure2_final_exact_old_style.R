suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly=TRUE)
option_value <- function(name, default) {
  index <- match(name, args)
  if (is.na(index)) return(default)
  if (index == length(args)) stop(sprintf("Missing value after %s", name))
  args[[index + 1L]]
}
summary_path <- option_value("--summary", "figure2_summary.csv")
outdir <- option_value("--output-dir", ".")

methods_main <- c(
  "KSSD-Array",
  "XXH3",
  "XXH64",
  "MurmurHash3",
  "Wyhash"
)

method_colors <- c(
  "KSSD-Array" = "#1F77B4",
  "XXH3" = "#FF7F0E",
  "XXH64" = "#2CA02C",
  "MurmurHash3" = "#D62728",
  "Wyhash" = "#9467BD"
)

method_linetypes <- c(
  "KSSD-Array" = "solid",
  "XXH3" = "dashed",
  "XXH64" = "dotdash",
  "MurmurHash3" = "dashed",
  "Wyhash" = "dotted"
)

method_shapes <- c(
  "KSSD-Array" = 16,
  "XXH3" = 15,
  "XXH64" = 17,
  "MurmurHash3" = 18,
  "Wyhash" = 25
)

method_labels <- c(
  "KSSD-Array" = "KSSD-Array",
  "XXH3" = "XXH3",
  "XXH64" = "XXH64",
  "MurmurHash3" = "MurmurHash3",
  "Wyhash" = "wyhash"
)

dataset_levels <- c("Synthetic_300M", "Human_GRCh38")
dataset_labels <- c(
  "Synthetic_300M" = "Synthetic 300 Mb",
  "Human_GRCh38" = "GRCh38.p14 chr1"
)

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

method_scales <- function(breaks) {
  list(
    scale_color_manual(name="Method", values=method_colors, breaks=breaks, labels=method_labels[breaks]),
    scale_fill_manual(name="Method", values=method_colors, breaks=breaks, labels=method_labels[breaks]),
    scale_shape_manual(name="Method", values=method_shapes, breaks=breaks, labels=method_labels[breaks]),
    scale_linetype_manual(name="Method", values=method_linetypes, breaks=breaks, labels=method_labels[breaks]),
    guides(
      color=guide_legend(
        title="Method",
        ncol=1,
        byrow=TRUE,
        override.aes=list(
          shape=unname(method_shapes[breaks]),
          linetype=unname(method_linetypes[breaks]),
          fill=unname(method_colors[breaks]),
          linewidth=ifelse(breaks == "KSSD-Array", 0.92, 0.62),
          size=2.4
        )
      ),
      fill="none",
      shape="none",
      linetype="none"
    )
  )
}

save_plot <- function(plot_obj, stem, width, height) {
  ggsave(file.path(outdir, paste0(stem, ".png")), plot_obj,
         width=width, height=height, dpi=300, bg="white")
  ggsave(file.path(outdir, paste0(stem, ".pdf")), plot_obj,
         width=width, height=height, bg="white")
}

# Figure 4.1: same summary rows and geometry as the selected original.
raw1 <- read.csv(summary_path)
if (nrow(raw1) != 150L) stop(sprintf("Expected 150 final Figure 2 rows, found %d", nrow(raw1)))
raw1$method[raw1$method == "KSSD-Array"] <- "KSSD-Array"
raw1$method[tolower(raw1$method) == "wyhash"] <- "Wyhash"
raw1$dataset[raw1$dataset == "Synthetic_300_Mb"] <- "Synthetic_300M"
raw1$dataset[raw1$dataset == "GRCh38.p14_chr1"] <- "Human_GRCh38"
raw1 <- subset(raw1, method %in% methods_main)
raw1$method <- factor(raw1$method, levels=methods_main)
raw1$dataset <- factor(raw1$dataset, levels=dataset_levels)
raw1$dataset_label <- factor(
  dataset_labels[as.character(raw1$dataset)],
  levels=dataset_labels[dataset_levels]
)
raw1$w <- factor(raw1$w, levels=c(10, 20, 50))
raw1$w_label <- factor(
  paste0("w = ", raw1$w),
  levels=c("w = 10", "w = 20", "w = 50")
)

p1 <- ggplot(
  raw1,
  aes(x=factor(k), y=throughput_mwindows_s_mean, color=method, fill=method,
      shape=method, linetype=method, group=method)
) +
  geom_line(data=subset(raw1, method != "KSSD-Array"), linewidth=0.55, alpha=0.90) +
  geom_point(data=subset(raw1, method != "KSSD-Array"), size=1.35, stroke=0.25, alpha=0.95) +
  geom_line(data=subset(raw1, method == "KSSD-Array"), linewidth=0.92, alpha=0.98) +
  geom_point(data=subset(raw1, method == "KSSD-Array"), size=1.85, stroke=0.25, alpha=0.98) +
  facet_grid(dataset_label ~ w_label) +
  method_scales(methods_main) +
  theme_kssd(9) +
  labs(x="k-mer length (k)", y="Throughput (M windows/s)")

save_plot(
  p1,
  "Figure2_final_exact_old_style",
  10.0,
  5.1
)
