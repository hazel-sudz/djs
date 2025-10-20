```
Data structure:
'data.frame':	49189 obs. of  63 variables:
 $ station                        : chr  "BOS" "BOS" "BOS" "BOS" ...
 $ valid                          : POSIXct, format: "2025-08-01 15:54:00" "2025-08-01 15:54:00" ...
 $ met_lon_ASOS                   : num  -71 -71 -71 -71 -71 ...
 $ met_lat_ASOS                   : num  42.4 42.4 42.4 42.4 42.4 ...
 $ elevation                      : num  9 9 9 9 9 9 9 9 9 9 ...
 $ tmpf                           : num  70 70 70 70 70 70 70 70 70 70 ...
 $ dwpf                           : num  58 58 58 58 58 58 58 58 58 58 ...
 $ relh                           : num  65.7 65.7 65.7 65.7 65.7 ...
 $ wd                             : num  60 60 60 60 60 60 60 60 60 60 ...
 $ met_kt                         : num  12 12 12 12 12 12 12 12 12 12 ...
 $ p01i                           : num  0 0 0 0 0 0 0 0 0 0 ...
 $ alti                           : num  30.2 30.2 30.2 30.2 30.2 ...
 $ mslp                           : num  1022 1022 1022 1022 1022 ...
 $ vsby                           : num  10 10 10 10 10 10 10 10 10 10 ...
 $ gust                           : num  18 18 18 18 18 18 18 18 18 18 ...
 $ skyc1                          : chr  "FEW" "FEW" "FEW" "FEW" ...
 $ skyc2                          : chr  "FEW" "FEW" "FEW" "FEW" ...
 $ skyc3                          : chr  "FEW" "FEW" "FEW" "FEW" ...
 $ skyc4                          : chr  NA NA NA NA ...
 $ skyl1                          : num  2500 2500 2500 2500 2500 2500 2500 2500 2500 2500 ...
 $ skyl2                          : num  14000 14000 14000 14000 14000 14000 14000 14000 14000 14000 ...
 $ skyl3                          : num  25000 25000 25000 25000 25000 25000 25000 25000 25000 25000 ...
 $ skyl4                          : num  NA NA NA NA NA NA NA NA NA NA ...
 $ wxcodes                        : chr  NA NA NA NA ...
 $ ice_accretion_1hr              : logi  NA NA NA NA NA NA ...
 $ feel                           : num  70 70 70 70 70 70 70 70 70 70 ...
 $ metar                          : chr  "KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144" "KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144" "KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144" "KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144" ...
 $ timestamp                      : POSIXct, format: "2025-08-01 15:30:18" "2025-08-01 15:30:58" ...
 $ cpc_particle_number_conc_corr.x: num  1855 2715 2855 2387 2353 ...
 $ flag                           : int  0 0 0 0 0 0 0 0 0 0 ...
 $ met.wx_dew_point               : num  16.1 16.2 16.3 16.2 16.1 ...
 $ met.wx_pressure                : num  1022 1022 1022 1022 1022 ...
 $ met.wx_rh                      : num  77.2 77.2 77 76.4 75.8 ...
 $ met.wx_temp                    : num  20.3 20.3 20.5 20.5 20.5 ...
 $ met.wx_u                       : num  0.966 1.143 1.318 1.023 1.063 ...
 $ met.wx_v                       : num  0.607 0.06 0.098 0.353 1.052 ...
 $ met.wx_wd                      : num  57.8 87 85.7 71 45.3 ...
 $ met.wx_ws                      : num  1.14 1.14 1.32 1.08 1.5 1.39 2.47 1.72 2.15 1.56 ...
 $ met.wx_ws_scalar               : num  1.2 1.26 1.46 1.19 1.56 1.59 2.63 1.76 2.34 1.6 ...
 $ sample_rh                      : num  61.3 61 61 60.7 60.1 59.5 58.8 58.1 57.5 57.2 ...
 $ sample_temp                    : num  24.6 24.8 25 25.2 25.5 25.7 26 26.2 26.4 26.5 ...
 $ sn.x                           : chr  "MOD-UFP-00007" "MOD-UFP-00007" "MOD-UFP-00007" "MOD-UFP-00007" ...
 $ timestamp_local.x              : POSIXct, format: "2025-08-01 11:30:18" "2025-08-01 11:30:58" ...
 $ url.x                          : chr  "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401456" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401459" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401458" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401457" ...
 $ cpc_particle_number_conc_corr.y: num  1855 2715 2855 2387 2353 ...
 $ lat                            : num  NA NA NA NA NA NA NA NA NA NA ...
 $ lon                            : num  NA NA NA NA NA NA NA NA NA NA ...
 $ met_wx_dew_point               : num  16.1 16.2 16.3 16.2 16.1 ...
 $ met_wx_pressure                : num  1022 1022 1022 1022 1022 ...
 $ met_wx_rh                      : num  77.2 77.2 77 76.4 75.8 ...
 $ met_wx_temp                    : num  20.3 20.3 20.5 20.5 20.5 ...
 $ met_wx_u                       : num  0.966 1.143 1.318 1.023 1.063 ...
 $ met_wx_v                       : num  0.607 0.06 0.098 0.353 1.052 ...
 $ met_wx_wd                      : num  57.8 87 85.7 71 45.3 ...
 $ met_wx_ws                      : num  1.14 1.14 1.32 1.08 1.5 1.39 2.47 1.72 2.15 1.56 ...
 $ met_wx_ws_scalar               : num  1.2 1.26 1.46 1.19 1.56 1.59 2.63 1.76 2.34 1.6 ...
 $ raw_data_id                    : int  401456 401459 401458 401457 401464 401467 401466 401465 401472 401473 ...
 $ sn.y                           : chr  "MOD-UFP-00007" "MOD-UFP-00007" "MOD-UFP-00007" "MOD-UFP-00007" ...
 $ timestamp_local.y              : POSIXct, format: "2025-08-01 11:30:18" "2025-08-01 11:30:58" ...
 $ url.y                          : chr  "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401452" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401455" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401454" "https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401453" ...
 $ geo.lat                        : num  NA NA NA NA NA NA NA NA NA NA ...
 $ geo.lon                        : num  NA NA NA NA NA NA NA NA NA NA ...
 $ ws                             : num  6.17 6.17 6.17 6.17 6.17 ...

Data dimensions:
[1] 49189    63

Column names:
 [1] "station"                         "valid"                          
 [3] "met_lon_ASOS"                    "met_lat_ASOS"                   
 [5] "elevation"                       "tmpf"                           
 [7] "dwpf"                            "relh"                           
 [9] "wd"                              "met_kt"                         
[11] "p01i"                            "alti"                           
[13] "mslp"                            "vsby"                           
[15] "gust"                            "skyc1"                          
[17] "skyc2"                           "skyc3"                          
[19] "skyc4"                           "skyl1"                          
[21] "skyl2"                           "skyl3"                          
[23] "skyl4"                           "wxcodes"                        
[25] "ice_accretion_1hr"               "feel"                           
[27] "metar"                           "timestamp"                      
[29] "cpc_particle_number_conc_corr.x" "flag"                           
[31] "met.wx_dew_point"                "met.wx_pressure"                
[33] "met.wx_rh"                       "met.wx_temp"                    
[35] "met.wx_u"                        "met.wx_v"                       
[37] "met.wx_wd"                       "met.wx_ws"                      
[39] "met.wx_ws_scalar"                "sample_rh"                      
[41] "sample_temp"                     "sn.x"                           
[43] "timestamp_local.x"               "url.x"                          
[45] "cpc_particle_number_conc_corr.y" "lat"                            
[47] "lon"                             "met_wx_dew_point"               
[49] "met_wx_pressure"                 "met_wx_rh"                      
[51] "met_wx_temp"                     "met_wx_u"                       
[53] "met_wx_v"                        "met_wx_wd"                      
[55] "met_wx_ws"                       "met_wx_ws_scalar"               
[57] "raw_data_id"                     "sn.y"                           
[59] "timestamp_local.y"               "url.y"                          
[61] "geo.lat"                         "geo.lon"                        
[63] "ws"                             

First few rows:
  station               valid met_lon_ASOS met_lat_ASOS elevation tmpf dwpf
1     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
2     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
3     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
4     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
5     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
6     BOS 2025-08-01 15:54:00     -71.0097      42.3606         9   70   58
   relh wd met_kt p01i  alti   mslp vsby gust skyc1 skyc2 skyc3 skyc4 skyl1
1 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
2 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
3 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
4 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
5 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
6 65.72 60     12    0 30.19 1022.3   10   18   FEW   FEW   FEW  <NA>  2500
  skyl2 skyl3 skyl4 wxcodes ice_accretion_1hr feel
1 14000 25000    NA    <NA>                NA   70
2 14000 25000    NA    <NA>                NA   70
3 14000 25000    NA    <NA>                NA   70
4 14000 25000    NA    <NA>                NA   70
5 14000 25000    NA    <NA>                NA   70
6 14000 25000    NA    <NA>                NA   70
                                                                                   metar
1 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
2 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
3 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
4 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
5 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
6 KBOS 011554Z 06012G18KT 10SM FEW025 FEW140 FEW250 21/14 A3019 RMK AO2 SLP223 T02110144
            timestamp cpc_particle_number_conc_corr.x flag met.wx_dew_point
1 2025-08-01 15:30:18                          1855.2    0            16.13
2 2025-08-01 15:30:58                          2714.7    0            16.17
3 2025-08-01 15:31:58                          2854.8    0            16.33
4 2025-08-01 15:32:58                          2386.8    0            16.20
5 2025-08-01 15:33:58                          2353.3    0            16.07
6 2025-08-01 15:34:58                          2298.2    0            15.93
  met.wx_pressure met.wx_rh met.wx_temp met.wx_u met.wx_v met.wx_wd met.wx_ws
1         1022.05     77.18       20.27    0.966    0.607     57.83      1.14
2         1022.10     77.15       20.32    1.143    0.060     86.99      1.14
3         1022.10     76.98       20.48    1.318    0.098     85.74      1.32
4         1022.18     76.38       20.50    1.023    0.353     70.95      1.08
5         1022.13     75.77       20.48    1.063    1.052     45.30      1.50
6         1022.10     75.08       20.50    1.233    0.649     62.24      1.39
  met.wx_ws_scalar sample_rh sample_temp          sn.x   timestamp_local.x
1             1.20      61.3        24.6 MOD-UFP-00007 2025-08-01 11:30:18
2             1.26      61.0        24.8 MOD-UFP-00007 2025-08-01 11:30:58
3             1.46      61.0        25.0 MOD-UFP-00007 2025-08-01 11:31:58
4             1.19      60.7        25.2 MOD-UFP-00007 2025-08-01 11:32:58
5             1.56      60.1        25.5 MOD-UFP-00007 2025-08-01 11:33:58
6             1.59      59.5        25.7 MOD-UFP-00007 2025-08-01 11:34:58
                                                              url.x
1 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401456
2 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401459
3 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401458
4 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401457
5 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401464
6 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/raw/401467
  cpc_particle_number_conc_corr.y lat lon met_wx_dew_point met_wx_pressure
1                          1855.2  NA  NA            16.13         1022.05
2                          2714.7  NA  NA            16.17         1022.10
3                          2854.8  NA  NA            16.33         1022.10
4                          2386.8  NA  NA            16.20         1022.18
5                          2353.3  NA  NA            16.07         1022.13
6                          2298.2  NA  NA            15.93         1022.10
  met_wx_rh met_wx_temp met_wx_u met_wx_v met_wx_wd met_wx_ws met_wx_ws_scalar
1     77.18       20.27    0.966    0.607     57.83      1.14             1.20
2     77.15       20.32    1.143    0.060     86.99      1.14             1.26
3     76.98       20.48    1.318    0.098     85.74      1.32             1.46
4     76.38       20.50    1.023    0.353     70.95      1.08             1.19
5     75.77       20.48    1.063    1.052     45.30      1.50             1.56
6     75.08       20.50    1.233    0.649     62.24      1.39             1.59
  raw_data_id          sn.y   timestamp_local.y
1      401456 MOD-UFP-00007 2025-08-01 11:30:18
2      401459 MOD-UFP-00007 2025-08-01 11:30:58
3      401458 MOD-UFP-00007 2025-08-01 11:31:58
4      401457 MOD-UFP-00007 2025-08-01 11:32:58
5      401464 MOD-UFP-00007 2025-08-01 11:33:58
6      401467 MOD-UFP-00007 2025-08-01 11:34:58
                                                          url.y geo.lat geo.lon
1 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401452      NA      NA
2 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401455      NA      NA
3 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401454      NA      NA
4 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401453      NA      NA
5 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401460      NA      NA
6 https://api.quant-aq.com/v1/devices/MOD-UFP-00007/data/401463      NA      NA
        ws
1 6.173333
2 6.173333
3 6.173333
4 6.173333
5 6.173333
6 6.173333

Data summary:
   station              valid                      met_lon_ASOS   
 Length:49189       Min.   :2025-08-01 15:54:00   Min.   :-71.01  
 Class :character   1st Qu.:2025-08-04 13:54:00   1st Qu.:-71.01  
 Mode  :character   Median :2025-08-07 09:54:00   Median :-71.01  
                    Mean   :2025-08-07 11:27:41   Mean   :-71.01  
                    3rd Qu.:2025-08-10 06:54:00   3rd Qu.:-71.01  
                    Max.   :2025-08-12 23:54:00   Max.   :-71.01  
                                                                  
  met_lat_ASOS     elevation      tmpf            dwpf            relh      
 Min.   :42.36   Min.   :9   Min.   :60.00   Min.   :44.00   Min.   :31.66  
 1st Qu.:42.36   1st Qu.:9   1st Qu.:67.00   1st Qu.:55.00   1st Qu.:53.71  
 Median :42.36   Median :9   Median :71.00   Median :58.00   Median :63.53  
 Mean   :42.36   Mean   :9   Mean   :71.97   Mean   :58.24   Mean   :63.70  
 3rd Qu.:42.36   3rd Qu.:9   3rd Qu.:76.00   3rd Qu.:62.00   3rd Qu.:73.34  
 Max.   :42.36   Max.   :9   Max.   :89.00   Max.   :66.00   Max.   :93.27  
                                                                            
       wd            met_kt            p01i                alti      
 Min.   :  0.0   Min.   : 0.000   Min.   :0.000e+00   Min.   :29.95  
 1st Qu.: 80.0   1st Qu.: 5.000   1st Qu.:0.000e+00   1st Qu.:30.13  
 Median :130.0   Median : 7.000   Median :0.000e+00   Median :30.20  
 Mean   :149.3   Mean   : 6.968   Mean   :7.319e-07   Mean   :30.21  
 3rd Qu.:210.0   3rd Qu.: 9.000   3rd Qu.:0.000e+00   3rd Qu.:30.29  
 Max.   :360.0   Max.   :16.000   Max.   :1.000e-04   Max.   :30.45  
 NA's   :717                                                         
      mslp           vsby             gust          skyc1          
 Min.   :1014   Min.   : 5.000   Min.   :16.00   Length:49189      
 1st Qu.:1020   1st Qu.:10.000   1st Qu.:16.00   Class :character  
 Median :1023   Median :10.000   Median :16.00   Mode  :character  
 Mean   :1023   Mean   : 9.687   Mean   :16.47                     
 3rd Qu.:1026   3rd Qu.:10.000   3rd Qu.:16.00                     
 Max.   :1031   Max.   :10.000   Max.   :18.00                     
 NA's   :271                     NA's   :48954                     
    skyc2              skyc3              skyc4               skyl1      
 Length:49189       Length:49189       Length:49189       Min.   :  500  
 Class :character   Class :character   Class :character   1st Qu.: 6000  
 Mode  :character   Mode  :character   Mode  :character   Median :22000  
                                                          Mean   :17070  
                                                          3rd Qu.:25000  
                                                          Max.   :25000  
                                                          NA's   :10961  
     skyl2           skyl3           skyl4         wxcodes         
 Min.   :14000   Min.   :25000   Min.   : NA     Length:49189      
 1st Qu.:22000   1st Qu.:25000   1st Qu.: NA     Class :character  
 Median :25000   Median :25000   Median : NA     Mode  :character  
 Mean   :22972   Mean   :25000   Mean   :NaN                       
 3rd Qu.:25000   3rd Qu.:25000   3rd Qu.: NA                       
 Max.   :25000   Max.   :25000   Max.   : NA                       
 NA's   :33464   NA's   :45195   NA's   :49189                     
 ice_accretion_1hr      feel          metar          
 Mode:logical      Min.   :60.00   Length:49189      
 NA's:49189        1st Qu.:67.00   Class :character  
                   Median :71.00   Mode  :character  
                   Mean   :72.08                     
                   3rd Qu.:76.00                     
                   Max.   :90.41                     
                                                     
   timestamp                   cpc_particle_number_conc_corr.x      flag  
 Min.   :2025-08-01 15:30:18   Min.   :    1251                Min.   :0  
 1st Qu.:2025-08-04 13:45:45   1st Qu.:    6578                1st Qu.:0  
 Median :2025-08-07 10:11:01   Median :   12323                Median :0  
 Mean   :2025-08-07 11:44:31   Mean   :   33918                Mean   :0  
 3rd Qu.:2025-08-10 06:35:59   3rd Qu.:   32695                3rd Qu.:0  
 Max.   :2025-08-13 14:26:13   Max.   :48484689                Max.   :0  
                               NA's   :573                     NA's   :1  
 met.wx_dew_point met.wx_pressure    met.wx_rh      met.wx_temp   
 Min.   : 3.83    Min.   : 511.1   Min.   :27.15   Min.   : 9.70  
 1st Qu.:13.25    1st Qu.:1019.5   1st Qu.:55.58   1st Qu.:19.60  
 Median :15.40    Median :1021.9   Median :65.82   Median :21.77  
 Mean   :15.04    Mean   :1022.1   Mean   :65.12   Mean   :22.32  
 3rd Qu.:17.17    3rd Qu.:1024.8   3rd Qu.:75.03   3rd Qu.:24.50  
 Max.   :22.00    Max.   :1030.9   Max.   :97.30   Max.   :33.83  
 NA's   :1        NA's   :1        NA's   :1       NA's   :1      
    met.wx_u          met.wx_v         met.wx_wd       met.wx_ws     
 Min.   :-3.3400   Min.   :-3.2670   Min.   :  0.0   Min.   :0.0000  
 1st Qu.:-0.4070   1st Qu.:-0.3820   1st Qu.: 98.1   1st Qu.:0.3000  
 Median : 0.0550   Median :-0.0860   Median :152.2   Median :0.6700  
 Mean   : 0.2984   Mean   :-0.1172   Mean   :175.4   Mean   :0.9776  
 3rd Qu.: 0.7900   3rd Qu.: 0.1290   3rd Qu.:254.5   3rd Qu.:1.4300  
 Max.   : 5.8560   Max.   : 3.4580   Max.   :360.0   Max.   :6.4000  
 NA's   :1         NA's   :1         NA's   :1       NA's   :1       
 met.wx_ws_scalar   sample_rh      sample_temp        sn.x          
 Min.   :0.020    Min.   :27.40   Min.   :18.80   Length:49189      
 1st Qu.:0.410    1st Qu.:45.40   1st Qu.:24.70   Class :character  
 Median :0.740    Median :52.60   Median :28.00   Mode  :character  
 Mean   :1.063    Mean   :52.78   Mean   :28.52                     
 3rd Qu.:1.500    3rd Qu.:60.00   3rd Qu.:31.50                     
 Max.   :6.420    Max.   :76.40   Max.   :44.40                     
 NA's   :1        NA's   :1       NA's   :1                         
 timestamp_local.x                url.x          
 Min.   :2025-08-01 11:30:18   Length:49189      
 1st Qu.:2025-08-04 09:45:38   Class :character  
 Median :2025-08-07 06:10:53   Mode  :character  
 Mean   :2025-08-07 07:44:20                     
 3rd Qu.:2025-08-10 02:35:46                     
 Max.   :2025-08-13 10:26:13                     
 NA's   :1                                       
 cpc_particle_number_conc_corr.y      lat             lon        
 Min.   :    1251                Min.   :42.36   Min.   :-71.03  
 1st Qu.:    6578                1st Qu.:42.36   1st Qu.:-71.03  
 Median :   12323                Median :42.36   Median :-71.00  
 Mean   :   33920                Mean   :42.37   Mean   :-71.00  
 3rd Qu.:   32699                3rd Qu.:42.38   3rd Qu.:-70.97  
 Max.   :48484689                Max.   :42.38   Max.   :-70.97  
 NA's   :572                     NA's   :12608   NA's   :12608   
 met_wx_dew_point met_wx_pressure    met_wx_rh      met_wx_temp   
 Min.   : 3.83    Min.   : 511.1   Min.   :27.15   Min.   : 9.70  
 1st Qu.:13.25    1st Qu.:1019.5   1st Qu.:55.58   1st Qu.:19.60  
 Median :15.40    Median :1021.9   Median :65.82   Median :21.77  
 Mean   :15.04    Mean   :1022.1   Mean   :65.12   Mean   :22.32  
 3rd Qu.:17.17    3rd Qu.:1024.8   3rd Qu.:75.03   3rd Qu.:24.50  
 Max.   :22.00    Max.   :1030.9   Max.   :97.30   Max.   :33.83  
                                                                  
    met_wx_u          met_wx_v         met_wx_wd       met_wx_ws     
 Min.   :-3.3400   Min.   :-3.2670   Min.   :  0.0   Min.   :0.0000  
 1st Qu.:-0.4070   1st Qu.:-0.3820   1st Qu.: 98.1   1st Qu.:0.3000  
 Median : 0.0550   Median :-0.0860   Median :152.2   Median :0.6700  
 Mean   : 0.2984   Mean   :-0.1172   Mean   :175.4   Mean   :0.9776  
 3rd Qu.: 0.7900   3rd Qu.: 0.1290   3rd Qu.:254.5   3rd Qu.:1.4300  
 Max.   : 5.8560   Max.   : 3.4580   Max.   :360.0   Max.   :6.4000  
                                                                     
 met_wx_ws_scalar  raw_data_id         sn.y          
 Min.   :0.020    Min.   :401456   Length:49189      
 1st Qu.:0.410    1st Qu.:426258   Class :character  
 Median :0.740    Median :451859   Mode  :character  
 Mean   :1.063    Mean   :457594                     
 3rd Qu.:1.500    3rd Qu.:486095                     
 Max.   :6.420    Max.   :537160                     
                                                     
 timestamp_local.y                url.y              geo.lat     
 Min.   :2025-08-01 11:30:18   Length:49189       Min.   :42.36  
 1st Qu.:2025-08-04 09:45:45   Class :character   1st Qu.:42.36  
 Median :2025-08-07 06:11:01   Mode  :character   Median :42.36  
 Mean   :2025-08-07 07:44:31                      Mean   :42.37  
 3rd Qu.:2025-08-10 02:35:59                      3rd Qu.:42.38  
 Max.   :2025-08-13 10:26:13                      Max.   :42.38  
                                                  NA's   :12609  
    geo.lon             ws       
 Min.   :-71.03   Min.   :0.000  
 1st Qu.:-71.03   1st Qu.:2.572  
 Median :-71.00   Median :3.601  
 Mean   :-71.00   Mean   :3.585  
 3rd Qu.:-70.97   3rd Qu.:4.630  
 Max.   :-70.97   Max.   :8.231  
 NA's   :12609 
 ```