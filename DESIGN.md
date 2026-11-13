---
name: Talk Translate
description: A quiet, two-way translation surface for travelers.
colors:
  accent: "#286c50"
  page: "#f5f7f4"
  surface: "#ffffff"
  text: "#19251f"
  muted: "#59665f"
  line: "#e2e8e2"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(27px, 4vw, 39px)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.052em"
  body:
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
  label:
    fontFamily: "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "9px"
    fontWeight: 700
    letterSpacing: "0.11em"
rounded:
  sm: "7px"
  md: "9px"
  lg: "19px"
spacing:
  compact: "8px"
  standard: "16px"
  section: "22px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0 11px"
    height: "33px"
  language-select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "47px"
  translator-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: "22px 26px 23px"
---

# Design System: Talk Translate

## Overview

**Creative North Star: "Le passage de relais"**

Talk Translate is a calm wayfinding surface for a conversation between two people who do not share a language. The interface makes the pair of languages, the current speaker, and the translated response easy to locate without turning a short exchange into a sequence of setup screens.

The visual language is restrained and light: generous neutral space, a leaf-green action color, soft surfaces, and compact labels that help travelers scan controls quickly. The same system inverts its neutral tones for dark mode. Inter is the explicitly requested interface face; its size and weight changes, rather than a second family, establish hierarchy.

**Key Characteristics:**
- One green accent; neutral tones carry the rest of the interface.
- A centered, narrow work surface, designed to remain usable on a phone.
- Speaker and language changes are expressed as clear states, not decoration.

## Colors

The palette uses one green accent against paper-like neutrals, with semantic colors reserved for feedback.

### Primary
- **Leaf Green**: Primary action, selected language, focus, and active conversation controls. Keep it as the sole decorative accent.

### Neutral
- **Soft Paper**: The default page ground; the translator surface remains white in the light theme.
- **Ink**: Main headings and translated text.
- **Quiet Ink**: Supporting instructions, labels, and metadata.
- **Hairline**: Input outlines, separators, and quiet control boundaries.
- **Night Surface**: In dark mode, the page and surface use deep green-black neutrals; text and muted text are lifted to preserve contrast.

**The One Accent Rule.** Use green for the primary action and active state. Do not introduce additional decorative accent colors; reserve red for errors and other distinct colors for explicit status only.

## Typography

**Display Font:** Inter (with system-ui, -apple-system, and Segoe UI fallbacks)  
**Body Font:** Inter (same fallback stack)  
**Label/Mono Font:** No separate label face.

**Character:** Direct, compact, and readable at a glance. Inter is the user-specified font; a broad weight and size range supplies hierarchy without introducing another external font.

### Hierarchy
- **Display** (700, responsive 27–39px, 1.2 line height): The invitation at the top of the translation surface.
- **Title** (600–700, 12–18px): Translation result, conversation language, and panel title.
- **Body** (400, 13–15px): Instructions, editable text, and supporting copy.
- **Label** (700, 9–10px, 0.11em, uppercase): Compact language and field labels.

**The Scan-First Rule.** Keep labels short and high-contrast; use size and weight, not a second font, to distinguish the task from its controls.

## Layout

The page centers a single translation work surface in a 650px content column, inside a wider 1250px header/footer frame. The language pair is the first control row, the microphone is the primary interaction, and text entry and translation follow below. The history panel enters from the right and keeps the translation page visible behind a dimmed backdrop.

Below 600px, outer padding tightens, the language pair keeps its two-column relationship, and the history panel fills the available width. Use compact-to-standard spacing for related controls and larger gaps between the heading, microphone, and text area.

## Elevation & Depth

The translator surface uses one soft, offset shadow to lift it from the page. The history drawer uses a deeper edge shadow to distinguish its overlay. Within the work surface, borders and subtle tonal shifts—not stacked shadows—separate inputs and results.

### Shadow Vocabulary
- **Translator Surface** (`0 18px 54px rgba(27, 55, 39, .075), 0 2px 8px rgba(27, 55, 39, .035)`): Ambient separation from the page.
- **History Drawer** (`-16px 0 48px rgba(0,0,0,.12)`): Separates the open side panel from the dimmed page.

## Shapes

Controls use compact rounded rectangles and buttons use smaller corners; the main translator surface has the largest radius. The microphone is the only circular primary control. Thin neutral borders define fields and secondary controls.

## Components

### Buttons
- **Primary translation action:** Compact filled green button, 7px corners, white text, and an arrow. It becomes more saturated on hover and retains a visible keyboard focus ring.
- **Icon actions:** Small, neutral icon buttons for audio, copy, favorite, share, theme, and panel close. Active favorites and playback use the green soft surface.
- **Conversation action:** Text-and-arrow control that reports its pressed state and reveals the two speaker turns.

### Cards / Containers
- **Translator:** White surface, 19px corners, thin neutral outline, and a soft offset shadow; 22px vertical and 26px horizontal desktop padding, reduced on mobile.
- **Translation result:** Quiet green-tinted surface with language direction and supporting actions; the translated text remains the visual focus.

### Inputs / Fields
- **Language selectors:** Paired bordered controls with a flag, native select, and a separate swap button.
- **Text field:** Multiline entry with a character count, clear action, and explicit translate button. Focus adds a green-tinted outline.
- **Error:** A clearly announced, lightly tinted message that names the problem and a practical recovery.

### Navigation

The history control opens a right-side panel with two tabs: recent translations and favorites. The panel has a close button, empty states, reuse and delete actions, and a clear-list action; Escape closes it and focus returns to its opener.

### Microphone

The centered circular control exposes idle, listening, and processing states. Listening uses a restrained pulse; in conversation mode, two labeled microphone choices identify the current speaker and the app alternates them after each phrase.

## Do's and Don'ts

### Do:
- **Do** keep the language pair, microphone, and text entry in that task order.
- **Do** preserve visible focus, live status announcements, and reduced-motion behavior.
- **Do** use the same accent for selected and primary-action states in both themes.

### Don't:
- **Don't** add decorative colors, gradients, or external interface libraries.
- **Don't** obscure the translated phrase with controls or supporting metadata.
- **Don't** imply that source-language detection is known when the provider does not return it.
