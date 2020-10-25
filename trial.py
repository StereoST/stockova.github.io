from yahoo_fin.stock_info import *
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate

get_analysts_info("ERIC")
mydict = get_earnings("ERIC")

quarterly_eps = mydict["quarterly_results"]
yearly_rev = mydict["yearly_revenue_earnings"]
quarterly_rev = mydict["quarterly_revenue_earnings"]

quarterly_eps.plot(title="yearly revenue",xticks=([x for x in range(0,4)]))
quarterly_rev.plot(title="quarterly revenue",xticks=([x for x in range(0,4)]))
plt.show()