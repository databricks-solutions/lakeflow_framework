SELECT 
  cast(Message_Id as string) as key,
  to_json(
    map_concat(
      from_json(Message_payload, 'map<string,string>'), -- Parse JSON string into a map
      map('timestamp', cast(Message_Ts as string)) -- Add 'timestamp' as a string
    )
  ) AS value
FROM stream(v_kafka_sink_sample_source)