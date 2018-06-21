# Engines features

## Engine Configurations

To configure Engine driver Bridge Administrator need to open
`Module/Engines` tab on the admin board and `add` new or `edit` existed
engine. Next fields are available to be configured:

- `Engine` - dropdown menu with available engine drivers.
- `Engine name` - string which is shown to the instructor when they
chosing engine to use with the collection-group.
- `Host` - (optional) host name to connect with the engine through the
engine API
- `Token` - (optional) token to authorize API communication between
engine and bridge
- `Lti parameters` - (optional) parameters which is taken from the LTI
launch request and added to the Sequence `metadata` field, they will be
available in futher engine - bridge communication. (More explanation in
VPAL Driver/LTI parameters subsection.)
- `is_default` - checkbox field, if set engine is used as the default
one.

## LTI prameters

LTI parameters as csv in the appropriate text field. At launch LTI
request engine's LTI parameters are used for parsing launch parameters
and storing found key-value pairs in the Sequence `metadata` field if
parameter is successfully found.

### VPAL Driver

All found and stored LTI parameters automatically added to the recommend
request `body`, for example:

Engine parameter `lis_person_sourcedid`

VPAL Driver add it to the body in `/engine/api/activity/recommend`
request:

```json
{
    learner: <user_id>,
    collection: <collection_slug>
    lis_person_sourcedid: <value from the launch LTI request>
    sequence: [ # List of already taken activities
        {
            activity: <source_launch_url>,
            score: <score>,
            is_problem: Bool,
        },
        ....
    ],
}
```
