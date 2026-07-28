suppressPackageStartupMessages(library(ggplot2))

parse_arguments <- function(arguments) {
  result <- list(summary=NULL, output_dir=NULL)
  index <- 1
  while (index <= length(arguments)) {
    option <- arguments[[index]]
    if (option == "--summary" && index + 1 <= length(arguments)) {
      result$summary <- arguments[[index + 1]]
      index <- index + 2
    } else if (option == "--output-dir" && index + 1 <= length(arguments)) {
      result$output_dir <- arguments[[index + 1]]
      index <- index + 2
    } else {
      stop(paste("unknown or incomplete option:", option))
    }
  }
  if (is.null(result$summary) || is.null(result$output_dir)) {
    stop("usage: plot script --summary FILE --output-dir DIRECTORY")
  }
  result
}

options <- parse_arguments(commandArgs(trailingOnly=TRUE))
methods <- c("KSSD-Array", "XXH3", "XXH64", "MurmurHash3", "Wyhash")
colors <- c(
  "KSSD-Array"="#1F77B4",
  "XXH3"="#FF7F0E",
  "XXH64"="#2CA02C",
  "MurmurHash3"="#D62728",
  "Wyhash"="#9467BD"
)
shapes <- c(
  "KSSD-Array"=16,
  "XXH3"=15,
  "XXH64"=17,
  "MurmurHash3"=18,
  "Wyhash"=25
)

summary <- read.csv(options$summary, stringsAsFactors=FALSE)
required <- c(
  "dataset", "k", "w", "method", "throughput_mwindows_s_mean"
)
if (!all(required %in% names(summary))) {
  stop("summary CSV lacks required columns")
}
if (!setequal(unique(summary$method), methods)) {
  stop("summary CSV method set differs from the required five")
}

summary$method <- factor(summary$method, levels=methods)
summary$k <- factor(summary$k, levels=sort(unique(summary$k)))
summary$w_label <- factor(
  paste0("w = ", summary$w),
  levels=paste0("w = ", sort(unique(summary$w)))
)
summary$dataset_label <- gsub("_", " ", summary$dataset)

plot <- ggplot(
  summary,
  aes(
    x=k,
    y=throughput_mwindows_s_mean,
    color=method,
    shape=method,
    group=method
  )
) +
  geom_line(linewidth=0.65, alpha=0.9) +
  geom_point(size=2.0, stroke=0.3) +
  facet_grid(dataset_label ~ w_label, scales="free_y") +
  scale_color_manual(values=colors, breaks=methods, drop=FALSE) +
  scale_shape_manual(values=shapes, breaks=methods, drop=FALSE) +
  theme_classic(base_size=10, base_family="sans") +
  theme(
    legend.position="right",
    panel.grid.major.y=element_line(color="#E6E6E6", linewidth=0.28),
    panel.grid.major.x=element_blank(),
    strip.background=element_rect(
      fill="#F2F2F2", color="#BDBDBD", linewidth=0.35
    ),
    strip.text=element_text(face="bold")
  ) +
  labs(
    x="k-mer length (k)",
    y="Throughput (M windows/s)",
    color="Method",
    shape="Method"
  )

dir.create(options$output_dir, recursive=TRUE, showWarnings=FALSE)
png_path <- file.path(
  options$output_dir, "figure2_single_thread_realistic_kw.png"
)
pdf_path <- file.path(
  options$output_dir, "figure2_single_thread_realistic_kw.pdf"
)
ggsave(png_path, plot, width=10.0, height=5.1, dpi=300, bg="white")
ggsave(pdf_path, plot, width=10.0, height=5.1, bg="white")
