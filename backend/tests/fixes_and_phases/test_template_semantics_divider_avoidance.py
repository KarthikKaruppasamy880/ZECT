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
