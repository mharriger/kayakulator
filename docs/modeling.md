## Modeling Module ##

### Model Element Dependencies ###

The gunwale and chine 0 are at the top of the dependency tree for model elements, they depend only on their offsets and endpoints. The keel depends on both chine 0 and the gunwale for its endpoints, while the deckridge depends only on the gunwale. Any other chines depend on chine0 and the gunwale for their initial endpoints, although the user can adjust those endpoints if needed. All of these stringer dependencies depend only on the basic geometric model of the stringers, they do not depend on the modeled solid.

Frames do depend on the modeled solid of all stringers, as the intersection of the outer face of each stringer defines the basic shape of the frame. Frames have no dependents.

Final solid geometry depends on the intersection between stringer and frame solids. How this should be handled is an open question. It doesn't feel like a responsibility of the frame or the stringer, should it be handled at the overall kayak model level? What object should own the data for those solids then? Or should the model be resonsible for calculating the intersections and handing each model component the piece it needs to remove? Otherwise one or the other could be responsible for removing its piece, and then the final version of the other is simply the difference.
