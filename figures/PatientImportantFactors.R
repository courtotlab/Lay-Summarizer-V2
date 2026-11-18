library(ggplot2)
library(tidyr)
library(dplyr)
library(readr)
library(patchwork)
library(packcircles)
library(viridis)
library(showtext)
library(here)

font_add_google("Inter", "Inter")
showtext_auto()
showtext_opts(dpi = 600)

data <- read.csv(here("data","Patient_ImportantFactors.csv"))

packing <- circleProgressiveLayout(data$Counts, sizetype='area')
data <- cbind(data, packing)
dat.gg <- circleLayoutVertices(packing, npoints=50)


wrap_text <- function(text, width = 10) {
  sapply(text, function(x) {
    paste(strwrap(x, width = width), collapse = "\n")
  }, USE.NAMES = FALSE)
}

data$Question_wrapped <- wrap_text(data$Question, width = 20)


# Make the plot
Circles <- ggplot() + 
  
  # Make the bubbles
  geom_polygon(data = dat.gg, aes(x, y, group = id, fill=as.factor(id)), alpha = 0.5) +
  scale_fill_viridis(discrete = TRUE,
                     option = "magma",
                     begin = 0.5 )+
  # Add text in the center of each bubble + control its size
  geom_text(data = data, aes(x, y,label = Question_wrapped)) +
  scale_size_continuous(range = c(1,4)) +
  
  # labs(title = bquote('Patient perspectives on'~ bold('challenges faced when understanding research and how ')))+
  
  # General theme:
  theme_void() + 
  theme(legend.position="none") +
  coord_equal()

# showtext_end()
Circles
# ggsave("Figure5.2.png", Circles, width = 4, height = 5, dpi = 600)
