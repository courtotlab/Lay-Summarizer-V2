library(ggplot2)
library(dplyr)
library(ggstats)
library(patchwork)
library(tidyverse)
library(here)

df <- read.csv(here("data", "Human Review Data Sheet - QuestionsOnPatientThemes.csv"), na.strings = c("", "NA"))

Q1 <- df %>%
  select("Q1") %>%
  drop_na() %>%
  mutate(Q1 = factor(
    case_when(
      startsWith(trimws(Q1), "No, the lay summaries were not useful if I were deciding to participate") ~ "No",
      startsWith(trimws(Q1), "The lay summaries were useful for my understanding, and would help guide me if I were deciding to participate") ~ "Yes"
    ),
    levels = c("No", "Yes")
  ))

Q2 <- df %>%
  select("Q2") %>%
  drop_na()

likert_levels <- c("No", "Maybe", "Yes")
Q3 <- df %>%
  select("Q3") %>%
  drop_na() %>%
  mutate(across(Q3, ~ factor(.x, levels = likert_levels)))

update_geom_defaults("text", list(family = "Inter", fontface ="bold"))


Q1_plot <- gglikert_stacked(Q1) +
  scale_fill_manual(values = c("#E69F00", "#a6d96a"))

Q2_plot <- gglikert_stacked(Q2) +
  scale_fill_manual(values = c("#E69F00", "#a6d96a"))

Q3_plot <- gglikert_stacked(Q3) +
  scale_fill_manual(values = c("#E69F00", "#D9D9D9", "#a6d96a"), drop = FALSE)

combined <- (Q1_plot / Q2_plot / Q3_plot) &
  theme(text = element_text(family = "Inter"))

# ggsave(
#   filename = "Perspectives.pdf",
#   plot = combined,
#   device = cairo_pdf,
#   width = 8,
#   height = 6,
#   units = "in",
#   dpi = 300,
#   bg = "transparent"
# )
combined