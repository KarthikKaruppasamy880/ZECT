"""Present Studio V4 -- a Zinnia template layout's own decorative vertical
divider bar (a tall, narrow AUTO_SHAPE baked into the layout, e.g. the
"Gradient Bottom" master) must be treated as a protected region body
content is placed around, not through. Reproduced live via headed
Playwright against the real Zinnia "Gradient Bottom" layout: an
AI-generated body text box was placed directly across the layout's own
divider, and neither existing repair strategy could fix it after the
fact because it isn't a slide-level shape collision at all -- it's a
layout-level obstacle placement decision made before the deck is ever
rendered."""

from __future__ import annotations

from app.services.mentrix.presentation.template_semantics import (
    boxes_overlap,
    compute_safe_content_bounds,
)

# Real geometry captured from a live-generated deck against the Zinnia
# "Gradient Bottom" layout (EMU units).
SLIDE_CX, SLIDE_CY = 12192000, 6858000
DIVIDER_BAR = {"x": 3798743, "y": 941422, "cx": 160626, "cy": 7758113}
BODY_TEXTBOX = {"x": 320040, "y": 727259, "cx": 7886700, "cy": 502920}


def test_body_region_still_overlaps_divider_without_it_registered_as_protected():
    """Sanity check: the raw body placeholder geometry genuinely collides
    with the divider bar -- this isn't a false alarm."""
    assert boxes_overlap(BODY_TEXTBOX, DIVIDER_BAR, pad=0)


def test_safe_content_bounds_avoids_a_tall_narrow_divider_in_the_middle_third():
    """The divider sits at x=3798743 on a 12192000-wide slide (~31% across)
    -- inside the gap between the old "right half" (>45%) and "narrow left
    corner" (<25%) branches, which never shrunk width at all for this
    obstacle shape. Must now be avoided regardless of exact x position."""
    safe = compute_safe_content_bounds(
        slide_cx=SLIDE_CX,
        slide_cy=SLIDE_CY,
        body_regions=[BODY_TEXTBOX],
        protected_regions=[DIVIDER_BAR],
    )
    assert not boxes_overlap(safe, DIVIDER_BAR, pad=0)
    # Must still leave a usable content width, not collapse to nothing.
    assert safe["cx"] >= int(SLIDE_CX * 0.2)


def test_divider_on_the_right_third_is_still_avoided_by_shrinking_left():
    """Regression guard for the pre-existing 'obstacle on right half' case
    -- the new tall-narrow branch must not break it."""
    right_divider = {"x": 8500000, "y": 500000, "cx": 150000, "cy": 5800000}
    safe = compute_safe_content_bounds(
        slide_cx=SLIDE_CX,
        slide_cy=SLIDE_CY,
        body_regions=[{"x": 320040, "y": 727259, "cx": 8500000, "cy": 502920}],
        protected_regions=[right_divider],
    )
    assert not boxes_overlap(safe, right_divider, pad=0)


def test_no_protected_regions_leaves_body_region_untouched():
    safe = compute_safe_content_bounds(
        slide_cx=SLIDE_CX, slide_cy=SLIDE_CY, body_regions=[BODY_TEXTBOX], protected_regions=[]
    )
    assert safe == BODY_TEXTBOX


class TestComposeRegionsShrinksEveryRegionNotJustBodyAndVisual:
    """Real bug found via a SECOND live headed-Playwright regeneration
    after the body/visual-only fix above: the "Gradient Bottom" layout
    has exactly one placeholder (reassigned as title, per compose_regions'
    own fallback for a layout with no dedicated title type), so its
    subtitle region is always the else-branch fallback -- which the first
    fix's shrink loop (body/visual only) never touched. The subtitle
    region still collided with the divider and got painted as real slide
    text. Fixed by shrinking title/subtitle/body/visual uniformly."""

    def _gradient_bottom_layout(self):
        """A synthetic definition matching the real Zinnia "Gradient Bottom"
        layout's exact shape (one placeholder, no dedicated title type,
        plus the divider) -- NOT loaded from the real template file, so
        this test doesn't depend on the Zinnia master PPTX being
        registered/configured on the machine running it (CI has none)."""
        from app.services.mentrix.presentation.layout_composer import _layouts
        from app.services.mentrix.presentation.template_semantics import enrich_definition_semantics

        definition = {
            "slide_size": {"cx": SLIDE_CX, "cy": SLIDE_CY},
            "layouts": [
                {
                    "name": "Gradient Bottom",
                    "layout_id": "Gradient Bottom",
                    "placeholders": [
                        {
                            "type": "body",
                            "geometry": {"x": 320040, "y": 292608, "cx": 7886700, "cy": 379787},
                            "name": "Content Placeholder 2",
                        }
                    ],
                    "shapes": [
                        {"role": "PROTECTED_BRAND_ELEMENT", "geometry": DIVIDER_BAR, "name": "Rectangle 7"},
                        {
                            "role": "FOOTER",
                            "geometry": {"x": 180109, "y": 4686819, "cx": 290946, "cy": 273844},
                            "name": "Slide Number Placeholder 5",
                        },
                    ],
                }
            ],
        }
        enriched = enrich_definition_semantics(definition)
        return enriched, next(l for l in _layouts(enriched) if l.get("name") == "Gradient Bottom")

    def test_every_composed_region_avoids_the_real_layout_divider(self):
        from app.services.mentrix.presentation.layout_composer import compose_regions

        definition, layout = self._gradient_bottom_layout()
        regions = compose_regions(definition, layout, split_visual=True)
        divider = DIVIDER_BAR
        for key in ("title", "subtitle", "body", "visual"):
            region = regions[key]
            assert not boxes_overlap(region, divider, pad=0), f"{key} region still overlaps the divider: {region}"

    def test_subtitle_region_specifically_no_longer_collides(self):
        """The exact region the first fix missed."""
        from app.services.mentrix.presentation.layout_composer import compose_regions

        definition, layout = self._gradient_bottom_layout()
        regions = compose_regions(definition, layout, split_visual=True)
        assert not boxes_overlap(regions["subtitle"], DIVIDER_BAR, pad=0)
